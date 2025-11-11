from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import CampfireClub
from campfire.models import Club


def build_club_payload(club_id: str, name: str = "Test Club") -> Club:
    return Club.from_dict(
        {
            "id": club_id,
            "name": name,
            "game": "pokemongo",
            "visibility": "public",
            "amIMember": True,
            "avatarUrl": "",
            "badgeGrants": [],
            "createdByCommunityAmbassador": False,
            "creator": {
                "id": "creator-1",
                "username": "creator",
                "displayName": "Creator",
                "avatarUrl": "",
                "badges": [],
                "clubRoles": [],
                "clubRank": None,
            },
        }
    )


class StubCampfireClient:
    def __init__(self, clubs: dict[str, Club]):
        self._clubs = clubs

    def get_club(self, club_id: str) -> Club:
        return self._clubs[club_id]

    def resolve_club(self, _url: str) -> Club:
        # Fallback to the first club when URLs are used in tests.
        return next(iter(self._clubs.values()))


class AuthAndClubClaimTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("auth-register")
        self.login_url = reverse("auth-login")
        self.logout_url = reverse("auth-logout")
        self.lookup_url = reverse("campfire-club-lookup")
        self.password = "TrainerPass123"

    def _register(self, username: str) -> str:
        response = self.client.post(
            self.register_url,
            {"username": username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["token"]

    def _authenticate(self, token: str):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

    def _clear_auth(self):
        self.client.credentials()

    @patch("api.views.build_campfire_client")
    def test_user_registration_and_login(self, mock_build_client):
        mock_build_client.return_value = StubCampfireClient({})
        token = self._register("ash")
        self.assertTrue(token)

        self._clear_auth()
        response = self.client.post(
            self.login_url,
            {"username": "ash", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    @patch("api.views.build_campfire_client")
    def test_user_can_claim_club_and_prevent_others(self, mock_build_client):
        club_id = "11111111-1111-1111-1111-111111111111"
        mock_build_client.return_value = StubCampfireClient({club_id: build_club_payload(club_id)})

        token = self._register("ash")
        self._authenticate(token)

        response = self.client.get(self.lookup_url, {"club": club_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CampfireClub.objects.get(pk=club_id).owner.username, "ash")

        # Second user cannot claim the same club.
        self._clear_auth()
        token_two = self._register("misty")
        self._authenticate(token_two)
        response_two = self.client.get(self.lookup_url, {"club": club_id})
        self.assertEqual(response_two.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("already managed", response_two.data["detail"])

    @patch("api.views.build_campfire_client")
    def test_user_cannot_claim_multiple_clubs(self, mock_build_client):
        club_one = "22222222-2222-2222-2222-222222222222"
        club_two = "33333333-3333-3333-3333-333333333333"
        mock_build_client.return_value = StubCampfireClient(
            {
                club_one: build_club_payload(club_one, "One"),
                club_two: build_club_payload(club_two, "Two"),
            }
        )

        token = self._register("brock")
        self._authenticate(token)

        first = self.client.get(self.lookup_url, {"club": club_one})
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.get(self.lookup_url, {"club": club_two})
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already manage", second.data["detail"])

        club = CampfireClub.objects.get(pk=club_one)
        self.assertEqual(club.owner.username, "brock")
