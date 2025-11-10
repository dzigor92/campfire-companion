from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import CampfireToken
from .utils import build_fake_token


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
