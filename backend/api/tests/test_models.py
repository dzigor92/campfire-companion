from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from api.models import CampfireToken
from .utils import build_fake_token


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
