from unittest.mock import patch

from django.test import SimpleTestCase

from campfire.client import CampfireClient, CampfireConfig, PUBLIC_MEETUP_PREFIX
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
