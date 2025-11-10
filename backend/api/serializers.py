from __future__ import annotations

from rest_framework import serializers

from .models import CampfireClub, CampfireEvent, CampfireEventRSVP, CampfireMember, CampfireToken


class CampfireMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampfireMember
        fields = ("id", "display_name", "username", "avatar_url", "club_rank")


class CampfireTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampfireToken
        fields = ("id", "email", "expires_at", "created_at")
        read_only_fields = fields


class CampfireClubSerializer(serializers.ModelSerializer):
    creator = CampfireMemberSerializer(read_only=True, allow_null=True)

    class Meta:
        model = CampfireClub
        fields = (
            "id",
            "name",
            "game",
            "visibility",
            "avatar_url",
            "created_by_community_ambassador",
            "badge_grants",
            "creator",
        )


class CampfireEventRSVPSerializer(serializers.ModelSerializer):
    member = CampfireMemberSerializer()

    class Meta:
        model = CampfireEventRSVP
        fields = ("member", "status")


class CampfireEventSerializer(serializers.ModelSerializer):
    club = CampfireClubSerializer()
    creator = CampfireMemberSerializer(read_only=True, allow_null=True)
    rsvps = CampfireEventRSVPSerializer(many=True)

    class Meta:
        model = CampfireEvent
        fields = (
            "id",
            "name",
            "details",
            "address",
            "location",
            "cover_photo_url",
            "map_preview_url",
            "event_time",
            "event_end_time",
            "rsvp_status",
            "created_by_community_ambassador",
            "discord_interested",
            "badge_grants",
            "campfire_live_event_id",
            "campfire_live_event_name",
            "checked_in_members_count",
            "members_total",
            "club",
            "creator",
            "rsvps",
        )
