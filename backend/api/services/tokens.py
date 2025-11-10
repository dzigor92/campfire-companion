from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone


class InvalidCampfireToken(ValueError):
    """Raised when a Campfire JWT cannot be decoded."""


@dataclass(frozen=True)
class DecodedCampfireToken:
    token: str
    email: str
    expires_at: datetime


def _decode_base64(segment: str) -> str:
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode((segment + padding).encode("utf-8")).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
        raise InvalidCampfireToken("Invalid token payload.") from exc


def parse_campfire_token(raw_token: str) -> DecodedCampfireToken:
    token = (raw_token or "").strip()
    if not token:
        raise InvalidCampfireToken("Token cannot be empty.")

    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidCampfireToken("Token must contain three segments.")

    payload_raw = _decode_base64(parts[1])
    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError as exc:
        raise InvalidCampfireToken("Token payload is not valid JSON.") from exc

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        raise InvalidCampfireToken("Token payload is missing an expiration timestamp.")

    email = payload.get("email") or payload.get("sub") or ""
    expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    return DecodedCampfireToken(token=token, email=email, expires_at=expires_at)
