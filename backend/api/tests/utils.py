import base64
import json
from datetime import timedelta

from django.utils import timezone


def _encode_segment(data: dict) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(data, separators=(",", ":")).encode("utf-8")
    ).decode("utf-8").rstrip("=")


def build_fake_token(
    email: str = "trainer@example.com", expires_delta: timedelta | None = None
) -> str:
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
