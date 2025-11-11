import base64
from typing import Any
from unittest.mock import patch
from urllib.parse import urlencode

from django.test import SimpleTestCase

from campfire.client import (
    CampfireClient,
    CampfireConfig,
    DISCOVER_MEETUP_PREFIX,
    MEETUP_SHORT_PREFIX,
    PUBLIC_MEETUP_PREFIX,
    PUBLIC_MEETUP_WITHOUT_LOCATION_PREFIX,
)
from campfire.exceptions import CampfireError, CampfireUnsupportedMeetup
from campfire.models import EventLocation, Events, Member, PublicEvent


class CampfireClientResolveEventTests(SimpleTestCase):
    def setUp(self):
        self.client = CampfireClient(config=CampfireConfig(), token_provider=lambda: "token")

    def _public_event(self, map_id: str, event_id: str) -> PublicEvent:
        return PublicEvent(
            map_object_id=map_id,
            event_id=event_id,
            name="",
            details="",
            club_name="",
            club_id="",
            club_avatar_url="",
            is_passcode_reward_eligible=False,
            event_time="",
            event_end_time="",
            address="",
            map_object_location=EventLocation(latitude=None, longitude=None),
        )

    def test_resolve_event_id_matches_correct_map_object(self):
        events = Events(
            public_map_objects_by_id=[
                self._public_event("mismatch", "camp-other"),
                self._public_event("target-public", "camp-target"),
            ]
        )
        with patch.object(self.client, "get_events", return_value=events):
            event_id = self.client.resolve_event_id(f"{PUBLIC_MEETUP_PREFIX}target-public")
        self.assertEqual(event_id, "camp-target")

    def test_expand_meetup_url_returns_same_for_non_short_links(self):
        url = f"{PUBLIC_MEETUP_PREFIX}target-public"
        self.assertEqual(self.client._expand_meetup_url(url), url)

    def test_expand_meetup_url_resolves_short_links(self):
        short_url = f"{MEETUP_SHORT_PREFIX}abcd"
        expanded_url = f"{DISCOVER_MEETUP_PREFIX}camp-123"
        with patch.object(self.client, "resolve_short_url", return_value=expanded_url) as resolver:
            result = self.client._expand_meetup_url(short_url)
        resolver.assert_called_once_with(short_url)
        self.assertEqual(result, expanded_url)

    def test_extract_event_id_from_meetup_handles_discover_links(self):
        discover_url = f"{DISCOVER_MEETUP_PREFIX}camp-987"
        self.assertEqual(self.client._extract_event_id_from_meetup(discover_url), "camp-987")

    def test_extract_event_id_from_meetup_rejects_without_location_links(self):
        with self.assertRaises(CampfireUnsupportedMeetup):
            self.client._extract_event_id_from_meetup(
                f"{PUBLIC_MEETUP_WITHOUT_LOCATION_PREFIX}target-public"
            )

    def test_extract_event_id_from_meetup_rejects_unknown_prefix(self):
        with self.assertRaises(CampfireError):
            self.client._extract_event_id_from_meetup("https://example.com/meetup/123")

    def test_extract_event_id_from_meetup_delegates_public_links(self):
        public_url = f"{PUBLIC_MEETUP_PREFIX}target-public"
        with patch.object(
            self.client, "_event_id_from_public_meetup", return_value="camp-target"
        ) as resolver:
            event_id = self.client._extract_event_id_from_meetup(public_url)
        resolver.assert_called_once_with(public_url)
        self.assertEqual(event_id, "camp-target")

    def test_event_id_from_public_meetup_returns_matching_event(self):
        events = Events(
            public_map_objects_by_id=[
                self._public_event("mismatch", "camp-other"),
                self._public_event("target-public", "camp-target"),
            ]
        )
        with patch.object(self.client, "get_events", return_value=events):
            event_id = self.client._event_id_from_public_meetup(
                f"{PUBLIC_MEETUP_PREFIX}target-public"
            )
        self.assertEqual(event_id, "camp-target")

    def test_event_id_from_public_meetup_requires_public_id_segment(self):
        with self.assertRaises(CampfireError):
            self.client._event_id_from_public_meetup(PUBLIC_MEETUP_PREFIX)


class CampfireClientResolveClubTests(SimpleTestCase):
    def setUp(self):
        self.client = CampfireClient(config=CampfireConfig(), token_provider=lambda: "token")

    def _encoded_payload(self, **params: str) -> str:
        query = urlencode(params)
        return base64.b64encode(query.encode()).decode()

    def _club_url(self, payload: dict[str, str] | None = None, include_param: bool = True) -> str:
        base_url = "https://campfire.test/club"
        if not include_param:
            return base_url
        payload = payload or {"r": "clubs", "c": "club-id"}
        encoded = self._encoded_payload(**payload)
        return f"{base_url}?deep_link_sub1={encoded}"

    def test_resolve_club_id_returns_club_id(self):
        club_url = self._club_url({"r": "clubs", "c": "club-123"})
        self.assertEqual(self.client.resolve_club_id(club_url), "club-123")

    def test_extract_deep_link_payload_requires_parameter(self):
        with self.assertRaises(CampfireError):
            self.client._extract_deep_link_payload(self._club_url(include_param=False))

    def test_decode_deep_link_payload_parses_querystring(self):
        encoded = self._encoded_payload(r="clubs", c="club-5")
        payload = self.client._decode_deep_link_payload(encoded)
        self.assertEqual(payload["r"][0], "clubs")
        self.assertEqual(payload["c"][0], "club-5")

    def test_club_id_from_payload_validates_route_type(self):
        payload = {"r": ["events"], "c": ["club-6"]}
        with self.assertRaises(CampfireError):
            self.client._club_id_from_payload(payload)

    def test_club_id_from_payload_requires_club_id(self):
        payload = {"r": ["clubs"], "c": [""]}
        with self.assertRaises(CampfireError):
            self.client._club_id_from_payload(payload)

    def test_resolve_club_fetches_data_via_data_source(self):
        club_id = "club-789"
        club_url = self._club_url({"r": "clubs", "c": club_id})

        class StubDataSource:
            def __init__(self):
                self.fetched: list[str] = []

            def fetch_club(self, requested_club_id: str) -> dict[str, Any]:
                self.fetched.append(requested_club_id)
                return {
                    "club": {
                        "id": requested_club_id,
                        "name": "Campfire Crew",
                        "game": "Ingress",
                        "visibility": "PUBLIC",
                        "amIMember": True,
                        "avatarUrl": "https://example.com/avatar.png",
                        "badgeGrants": ["badge-1"],
                        "createdByCommunityAmbassador": False,
                        "creator": {
                            "id": "creator-1",
                            "username": "leader",
                            "displayName": "Leader",
                            "avatarUrl": "",
                            "badges": [],
                            "clubRoles": [],
                            "clubRank": None,
                        },
                    }
                }

        data_source = StubDataSource()
        client = CampfireClient(
            config=CampfireConfig(),
            token_provider=lambda: "token",
            data_source=data_source,
        )

        club = client.resolve_club(club_url)

        self.assertEqual(club.id, club_id)
        self.assertEqual(club.name, "Campfire Crew")
        self.assertEqual(data_source.fetched, [club_id])


class CampfireMemberParsingTests(SimpleTestCase):
    def test_handles_null_badges_and_roles(self):
        member = Member.from_dict(
            {
                "id": "123",
                "username": "trainer",
                "displayName": "Trainer",
                "badges": None,
                "clubRoles": None,
            }
        )
        self.assertEqual(member.badges, [])
        self.assertEqual(member.club_roles, [])
