"""Integration helpers for wiring the shared Campfire client into Django."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import functools
import os
from typing import Callable

from django.conf import settings

from campfire import CampfireClient, CampfireConfig

from api.models import CampfireToken

TokenProvider = Callable[[], str | None]

@dataclass(frozen=True)
class CampfireSettings:
    every_seconds: int = 1
    burst: int = 40
    max_retries: int = 3
    token: str | None = None

    @classmethod
    def from_django(cls) -> "CampfireSettings":
        cfg = getattr(settings, "CAMPFIRE", {})
        return cls(
            every_seconds=int(cfg.get("EVERY_SECONDS", cls.every_seconds)),
            burst=int(cfg.get("BURST", cls.burst)),
            max_retries=int(cfg.get("MAX_RETRIES", cls.max_retries)),
            token=cfg.get("TOKEN"),
        )


@functools.lru_cache(maxsize=1)
def _cached_settings() -> CampfireSettings:
    return CampfireSettings.from_django()


def get_campfire_config() -> CampfireConfig:
    cfg = _cached_settings()
    return CampfireConfig(
        every=timedelta(seconds=cfg.every_seconds),
        burst=cfg.burst,
        max_retries=cfg.max_retries,
    )


def env_token_provider() -> TokenProvider:
    token = os.environ.get("CAMPFIRE_TOKEN") or _cached_settings().token

    def provider() -> str | None:
        return token

    return provider


def database_token_provider() -> TokenProvider:
    def provider() -> str | None:
        return CampfireToken.objects.valid().values_list("token", flat=True).first()

    return provider


def chained_token_provider(*providers: TokenProvider) -> TokenProvider:
    def provider() -> str | None:
        for candidate in providers:
            token = candidate()
            if token:
                return token
        return None

    return provider


def default_token_provider() -> TokenProvider:
    return chained_token_provider(env_token_provider(), database_token_provider())


def build_campfire_client(token_provider: TokenProvider | None = None) -> CampfireClient:
    provider = token_provider or default_token_provider()
    return CampfireClient(config=get_campfire_config(), token_provider=provider)
