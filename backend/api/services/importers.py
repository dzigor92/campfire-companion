from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from campfire.models import Club as CampfireClubData
from campfire.models import Event as CampfireEventData
from campfire.models import Member as CampfireMemberData
from campfire.models import find_member

from api.models import (
    CampfireClub,
    CampfireEvent,
    CampfireEventRSVP,
    CampfireMember,
)


def _parse_datetime(value: str | None):
    if not value:
        return timezone.now()
    parsed = parse_datetime(value)
    if parsed is None:
        return timezone.now()
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.utc)
    return parsed


def persist_member(member: CampfireMemberData) -> CampfireMember:
    obj, _ = CampfireMember.objects.update_or_create(
        id=member.id,
        defaults={
            "username": member.username or "",
            "display_name": member.display_name or "",
            "avatar_url": member.avatar_url or "",
            "club_rank": member.club_rank,
            "raw": member.raw or {},
        },
    )
    return obj


def persist_club(club: CampfireClubData) -> CampfireClub:
    creator = persist_member(club.creator) if club.creator and club.creator.id else None
    obj, _ = CampfireClub.objects.update_or_create(
        id=club.id,
        defaults={
            "name": club.name or "",
            "avatar_url": club.avatar_url or "",
            "game": club.game or "",
            "visibility": club.visibility or "",
            "created_by_community_ambassador": club.created_by_community_ambassador,
            "badge_grants": club.badge_grants,
            "creator": creator,
            "raw": club.raw or {},
        },
    )
    return obj


def _ensure_member(member_id: str, event: CampfireEventData):
    member_data = find_member(member_id, event)
    if member_data:
        return persist_member(member_data)
    obj, _ = CampfireMember.objects.get_or_create(
        id=member_id,
        defaults={
            "username": "",
            "display_name": "",
            "avatar_url": "",
            "raw": {},
        },
    )
    return obj


def persist_event(event: CampfireEventData) -> CampfireEvent:
    with transaction.atomic():
        club = persist_club(event.club)
        creator = persist_member(event.creator) if event.creator and event.creator.id else None

        obj, _ = CampfireEvent.objects.update_or_create(
            id=event.id,
            defaults={
                "name": event.name or "",
                "details": event.details or "",
                "address": event.address or "",
                "location": event.location or "",
                "cover_photo_url": event.cover_photo_url or "",
                "map_preview_url": event.map_preview_url or "",
                "event_time": _parse_datetime(event.event_time),
                "event_end_time": _parse_datetime(event.event_end_time)
                if event.event_end_time
                else None,
                "rsvp_status": event.rsvp_status or "",
                "created_by_community_ambassador": event.created_by_community_ambassador,
                "discord_interested": event.discord_interested,
                "badge_grants": event.badge_grants,
                "campfire_live_event_id": event.campfire_live_event_id or "",
                "campfire_live_event_name": (event.campfire_live_event.event_name or "")
                if event.campfire_live_event
                else "",
                "checked_in_members_count": event.checked_in_members_count or 0,
                "members_total": event.members.total_count,
                "club": club,
                "creator": creator,
                "raw": event.raw or {},
            },
        )

        member_ids = set()
        for edge in event.members.edges:
            member_model = persist_member(edge.node)
            member_ids.add(member_model.id)

        seen_rsvps: set[str] = set()
        for rsvp in event.rsvp_statuses:
            member_model = _ensure_member(rsvp.user_id, event)
            CampfireEventRSVP.objects.update_or_create(
                event=obj,
                member=member_model,
                defaults={"status": rsvp.rsvp_status},
            )
            seen_rsvps.add(member_model.id)

        CampfireEventRSVP.objects.filter(event=obj).exclude(member_id__in=seen_rsvps).delete()

        return obj
