from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, List, Optional, TypeVar


T = TypeVar("T")


@dataclass(slots=True)
class GraphQLError:
    message: str
    path: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphQLError":
        return cls(message=data.get("message", ""), path=list(data.get("path", [])))


@dataclass(slots=True)
class GraphQLResponse(Generic[T]):
    data: T
    errors: list[GraphQLError] = field(default_factory=list)


@dataclass(slots=True)
class PageInfo:
    has_next_page: bool
    start_cursor: Optional[str]
    end_cursor: Optional[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PageInfo":
        return cls(
            has_next_page=bool(data.get("hasNextPage")),
            start_cursor=data.get("startCursor"),
            end_cursor=data.get("endCursor"),
        )


@dataclass(slots=True)
class Edge(Generic[T]):
    node: T
    cursor: Optional[str]


@dataclass(slots=True)
class Pagination(Generic[T]):
    total_count: int
    edges: list[Edge[T]]
    page_info: PageInfo


@dataclass(slots=True)
class Badge:
    alias: Optional[str]
    badge_type: Optional[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Badge":
        return cls(alias=data.get("alias"), badge_type=data.get("badgeType"))


@dataclass(slots=True)
class ClubRole:
    id: str
    name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClubRole":
        return cls(id=data.get("id", ""), name=data.get("name", ""))


@dataclass(slots=True)
class Member:
    id: str
    username: str
    display_name: str
    avatar_url: str
    badges: list[Badge]
    club_roles: list[ClubRole]
    club_rank: Optional[int]
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Member":
        badges_data = data.get("badges") or []
        club_roles_data = data.get("clubRoles") or []
        return cls(
            id=data.get("id", ""),
            username=data.get("username", ""),
            display_name=data.get("displayName", ""),
            avatar_url=data.get("avatarUrl", ""),
            badges=[Badge.from_dict(b) for b in badges_data],
            club_roles=[ClubRole.from_dict(r) for r in club_roles_data],
            club_rank=data.get("clubRank"),
            raw=data,
        )


@dataclass(slots=True)
class CampfireLiveEvent:
    id: str
    check_in_radius_meters: Optional[int]
    event_name: Optional[str]
    modal_heading_image_url: Optional[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CampfireLiveEvent":
        data = data or {}
        return cls(
            id=data.get("id", ""),
            check_in_radius_meters=data.get("checkInRadiusMeters"),
            event_name=data.get("eventName"),
            modal_heading_image_url=data.get("modalHeadingImageUrl"),
        )


@dataclass(slots=True)
class Club:
    id: str
    name: str
    game: Optional[str]
    visibility: Optional[str]
    am_i_member: bool
    avatar_url: str
    badge_grants: list[str]
    created_by_community_ambassador: bool
    creator: Member
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Club":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            game=data.get("game"),
            visibility=data.get("visibility"),
            am_i_member=bool(data.get("amIMember")),
            avatar_url=data.get("avatarUrl", ""),
            badge_grants=list(data.get("badgeGrants", [])),
            created_by_community_ambassador=bool(data.get("createdByCommunityAmbassador")),
            creator=Member.from_dict(data.get("creator", {})),
            raw=data,
        )


@dataclass(slots=True)
class EventLocation:
    latitude: Optional[float]
    longitude: Optional[float]

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EventLocation":
        data = data or {}
        return cls(latitude=data.get("latitude"), longitude=data.get("longitude"))


@dataclass(slots=True)
class RSVPStatus:
    user_id: str
    rsvp_status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RSVPStatus":
        return cls(user_id=data.get("userId", ""), rsvp_status=data.get("rsvpStatus", ""))


@dataclass(slots=True)
class Event:
    id: str
    name: str
    visibility: Optional[str]
    address: str
    location: Optional[str]
    cover_photo_url: str
    map_preview_url: Optional[str]
    details: str
    event_time: str
    event_end_time: str
    rsvp_status: Optional[str]
    created_by_community_ambassador: bool
    badge_grants: list[str]
    topic_id: Optional[str]
    discord_interested: int
    game: Optional[str]
    creator: Member
    club_id: str
    club: Club
    members: Pagination[Member]
    checked_in_members_count: Optional[int]
    rsvp_statuses: list[RSVPStatus]
    is_passcode_reward_eligible: bool
    passcode: Optional[str]
    campfire_live_event_id: Optional[str]
    campfire_live_event: CampfireLiveEvent
    comments_permissions: Optional[str]
    comment_count: int
    is_subscribed: bool
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        members_data = data.get("members", {})
        member_edges: list[Edge[Member]] = []
        for edge in members_data.get("edges", []):
            member_edges.append(Edge(node=Member.from_dict(edge.get("node", {})), cursor=edge.get("cursor")))

        members = Pagination(
            total_count=members_data.get("totalCount", 0),
            edges=member_edges,
            page_info=PageInfo.from_dict(members_data.get("pageInfo", {})),
        )

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            visibility=data.get("visibility"),
            address=data.get("address", ""),
            location=data.get("location"),
            cover_photo_url=data.get("coverPhotoUrl", ""),
            map_preview_url=data.get("mapPreviewUrl"),
            details=data.get("details", ""),
            event_time=data.get("eventTime", ""),
            event_end_time=data.get("eventEndTime", ""),
            rsvp_status=data.get("rsvpStatus"),
            created_by_community_ambassador=bool(data.get("createdByCommunityAmbassador")),
            badge_grants=list(data.get("badgeGrants", [])),
            topic_id=data.get("topicId"),
            discord_interested=int(data.get("discordInterested", 0)),
            game=data.get("game"),
            creator=Member.from_dict(data.get("creator", {})),
            club_id=data.get("clubId", ""),
            club=Club.from_dict(data.get("club", {})),
            members=members,
            checked_in_members_count=data.get("checkedInMembersCount"),
            rsvp_statuses=[RSVPStatus.from_dict(r) for r in data.get("rsvpStatuses", [])],
            is_passcode_reward_eligible=bool(data.get("isPasscodeRewardEligible")),
            passcode=data.get("passcode"),
            campfire_live_event_id=data.get("campfireLiveEventId"),
            campfire_live_event=CampfireLiveEvent.from_dict(data.get("campfireLiveEvent")),
            comments_permissions=data.get("commentsPermissions"),
            comment_count=int(data.get("commentCount", 0)),
            is_subscribed=bool(data.get("isSubscribed")),
            raw=data,
        )


@dataclass(slots=True)
class PublicEvent:
    map_object_id: str
    event_id: str
    name: str
    details: str
    club_name: str
    club_id: str
    club_avatar_url: str
    is_passcode_reward_eligible: bool
    event_time: str
    event_end_time: str
    address: str
    map_object_location: EventLocation

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublicEvent":
        event = data.get("event", {})
        return cls(
            map_object_id=data.get("id", ""),
            event_id=event.get("id", ""),
            name=event.get("name", ""),
            details=event.get("details", ""),
            club_name=event.get("clubName", ""),
            club_id=event.get("clubId", ""),
            club_avatar_url=event.get("clubAvatarUrl", ""),
            is_passcode_reward_eligible=bool(event.get("isPasscodeRewardEligible")),
            event_time=event.get("eventTime", ""),
            event_end_time=event.get("eventEndTime", ""),
            address=event.get("address", ""),
            map_object_location=EventLocation.from_dict(event.get("mapObjectLocation")),
        )


@dataclass(slots=True)
class Events:
    public_map_objects_by_id: list[PublicEvent]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Events":
        return cls(
            public_map_objects_by_id=[PublicEvent.from_dict(item) for item in data.get("publicMapObjectsById", [])]
        )


def find_member(member_id: str, event: Event) -> Member | None:
    for edge in event.members.edges:
        if edge.node.id == member_id:
            return edge.node
    return None
