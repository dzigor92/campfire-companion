import base64
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import CampfireClub, CampfireMember, CampfireToken
from api.services.lookups import (
    ClubLookupError,
    extract_club_reference,
    normalize_club_lookup,
)
from campfire.client import CampfireClient, CampfireConfig, PUBLIC_MEETUP_PREFIX
from campfire.models import EventLocation, Events, Member, PublicEvent


def _encode_segment(data: dict) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(data, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8").rstrip("=")


def build_fake_token(email: str = "trainer@example.com", expires_delta: timedelta | None = None) -> str:
    expires_delta = expires_delta or timedelta(hours=1)
    exp = int((timezone.now() + expires_delta).timestamp())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "email": email,
        "exp": exp,
        "iat": exp - 3600,
        "iss": "campfire",
        "sub": email,
    }
    return f"{_encode_segment(header)}.{_encode_segment(payload)}.signature"


class ClubLookupParserTests(SimpleTestCase):
    def test_extracts_url_from_blob(self):
        raw = "See https://campfire.onelink.me/eBr8?deep_link_sub1=cj1jbHVicyZjPWI2&foo=bar please"
        club_url, club_id = extract_club_reference(raw)
        self.assertEqual(
            club_url,
            "https://campfire.onelink.me/eBr8?deep_link_sub1=cj1jbHVicyZjPWI2&foo=bar",
        )
        self.assertIsNone(club_id)

    def test_extracts_id_from_blob(self):
        club_url, club_id = extract_club_reference(
            "Club ID: b632fc8e-0b41-49de-ade2-21b0cd81db69"
        )
        self.assertIsNone(club_url)
        self.assertEqual(club_id, "b632fc8e-0b41-49de-ade2-21b0cd81db69")

    def test_raises_when_multiple_candidates_present(self):
        with self.assertRaises(ClubLookupError):
            extract_club_reference(
                "https://campfire.onelink.me/abcd?deep_link_sub1=foo "
                "and b632fc8e-0b41-49de-ade2-21b0cd81db69"
            )

    def test_strict_normalization_requires_reference(self):
        with self.assertRaises(ClubLookupError):
            normalize_club_lookup("no useful tokens here", strict=True)

    def test_non_strict_url_fallback(self):
        club_url, club_id = normalize_club_lookup(
            "https://example.com/not-onelink", default_kind="url"
        )
        self.assertEqual(club_url, "https://example.com/not-onelink")
        self.assertIsNone(club_id)

    def test_non_strict_id_fallback(self):
        club_url, club_id = normalize_club_lookup(
            "custom-club-id", default_kind="id"
        )
        self.assertIsNone(club_url)
        self.assertEqual(club_id, "custom-club-id")


class CampfireTokenQuerySetTests(TestCase):
    def test_valid_respects_one_minute_buffer(self):
        soon = CampfireToken.objects.create(
            token=build_fake_token(expires_delta=timedelta(minutes=1)),
            email="soon@example.com",
            expires_at=timezone.now() + timedelta(seconds=50),
        )
        later = CampfireToken.objects.create(
            token=build_fake_token(expires_delta=timedelta(hours=1)),
            email="later@example.com",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        valid_ids = list(CampfireToken.objects.valid().values_list("id", flat=True))
        self.assertNotIn(soon.id, valid_ids)
        self.assertIn(later.id, valid_ids)


class CampfireTokenAPITests(APITestCase):
    def setUp(self):
        self.url = reverse("campfire-tokens")

    def test_can_store_token(self):
        token = build_fake_token("ash@example.com", timedelta(minutes=10))
        response = self.client.post(self.url, {"token": token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "ash@example.com")
        self.assertIn("expires_at", response.data)
        self.assertEqual(CampfireToken.objects.count(), 1)

    def test_posting_again_updates_existing_token(self):
        token = build_fake_token("misty@example.com", timedelta(minutes=10))
        self.client.post(self.url, {"token": token}, format="json")
        response = self.client.post(self.url, {"token": token}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CampfireToken.objects.count(), 1)

    def test_rejects_invalid_token(self):
        response = self.client.post(self.url, {"token": "invalid"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_get_returns_only_valid_tokens(self):
        CampfireToken.objects.create(
            token=build_fake_token("brock@example.com", timedelta(minutes=5)),
            email="brock@example.com",
            expires_at=timezone.now() + timedelta(minutes=5),
        )
        CampfireToken.objects.create(
            token=build_fake_token("expired@example.com", timedelta(minutes=-5)),
            email="expired@example.com",
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["email"], "brock@example.com")


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


class CampfireImportClubHistoryTests(APITestCase):
    def setUp(self):
        self.url = reverse("campfire-import-club-history")
        self.creator = CampfireMember.objects.create(
            id="member-1",
            username="creator",
            display_name="Creator",
        )
        self.club = CampfireClub.objects.create(
            id="b632fc8e-0b41-49de-ade2-21b0cd81db69",
            name="Test Club",
            avatar_url="",
            game="pokemongo",
            visibility="public",
            creator=self.creator,
        )

    def _club_link(self) -> str:
        payload = base64.b64encode(f"r=clubs&c={self.club.id}".encode()).decode()
        return f"https://campfire.onelink.me/eBr8?deep_link_sub1={payload}"

    @patch("api.views.persist_event")
    @patch("api.views.persist_club")
    @patch("api.views.build_campfire_client")
    def test_imports_history(self, mock_build_client, mock_persist_club, mock_persist_event):
        mock_client = SimpleNamespace()
        event_ids = ["event-1", "event-2", "event-3"]
        mock_client.resolve_club = lambda _url: SimpleNamespace(id=self.club.id)
        mock_client.get_past_meetups = lambda _club_id: [SimpleNamespace(id=eid) for eid in event_ids]
        mock_build_client.return_value = mock_client
        mock_persist_club.return_value = self.club

        response = self.client.post(self.url, {"club": self._club_link()}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["events_imported"], len(event_ids))
        self.assertEqual(response.data["club"]["id"], self.club.id)
        self.assertEqual(mock_persist_event.call_count, len(event_ids))
