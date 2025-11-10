import base64
from types import SimpleNamespace
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import CampfireClub, CampfireMember


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
