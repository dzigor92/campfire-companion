from __future__ import annotations

from datetime import timedelta
import os
from typing import Callable

from django.conf import settings

from campfire import CampfireClient, CampfireConfig

from api.models import CampfireToken

TokenProvider = Callable[[], str | None]


def get_campfire_config() -> CampfireConfig:
    cfg = getattr(settings, "CAMPFIRE", {})
    return CampfireConfig(
        every=timedelta(seconds=cfg.get("EVERY_SECONDS", 1)),
        burst=cfg.get("BURST", 40),
        max_retries=cfg.get("MAX_RETRIES", 3),
    )


def default_token_provider() -> TokenProvider:
    env_token = (
        os.environ.get("CAMPFIRE_TOKEN")
        or getattr(settings, "CAMPFIRE", {}).get("TOKEN")
    )

    def provider() -> str | None:
        if env_token:
            return env_token
        return CampfireToken.objects.valid().values_list("token", flat=True).first()

    return provider


def build_campfire_client(token_provider: TokenProvider | None = None) -> CampfireClient:
    provider = token_provider or default_token_provider()
    return CampfireClient(config=get_campfire_config(), token_provider=provider)
