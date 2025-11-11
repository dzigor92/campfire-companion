"""Data source abstractions for retrieving Campfire data."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol

import requests

from .config import CampfireConfig, default_config
from .exceptions import (
    CampfireError,
    CampfireRateLimitError,
    CampfireRetryError,
)
from .models import GraphQLError
from .rate_limiter import RateLimiter
from .tokens import TokenProvider

logger = logging.getLogger(__name__)

PUBLIC_ENDPOINT = "https://niantic-social-api.nianticlabs.com/public/graphql"
PRIVATE_ENDPOINT = "https://niantic-social-api.nianticlabs.com/graphql"


class CampfireDataSource(Protocol):
    """Abstract source of Campfire data."""

    def resolve_short_url(self, url: str) -> tuple[str, str]:
        """Follow a short URL and return (final_url, response_body)."""

    def fetch_event(self, event_id: str) -> dict[str, Any]:
        """Fetch a full event payload."""

    def fetch_public_events(self, event_ids: Iterable[str]) -> dict[str, Any]:
        """Fetch public map objects by IDs."""

    def fetch_club(self, club_id: str) -> dict[str, Any]:
        """Fetch club details."""

    def fetch_archived_meetups(
        self,
        club_id: str,
        *,
        first: int,
        after: str | None,
        members_first: int,
    ) -> dict[str, Any]:
        """Fetch archived meetups for a club."""


class QueryStore:
    """Lazy loader for GraphQL query files."""

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}
        self._base_path = Path(__file__).parent / "queries"

    def get(self, name: str) -> str:
        if name not in self._cache:
            query_path = self._base_path / name
            self._cache[name] = query_path.read_text(encoding="utf-8")
        return self._cache[name]


QUERIES = QueryStore()


class GraphQLCampfireDataSource(CampfireDataSource):
    """GraphQL-backed implementation of the Campfire data source."""

    def __init__(
        self,
        config: CampfireConfig | None = None,
        token_provider: TokenProvider | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config or default_config()
        self.session = session or requests.Session()
        self.token_provider = token_provider
        self.rate_limiter = RateLimiter(self.config.every, self.config.burst)

    def resolve_short_url(self, url: str) -> tuple[str, str]:
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.url, response.text

    def fetch_event(self, event_id: str) -> dict[str, Any]:
        return self._private_query(
            QUERIES.get("event.graphql"),
            {
                "id": event_id,
                "first": 100000000,
            },
        )

    def fetch_public_events(self, event_ids: Iterable[str]) -> dict[str, Any]:
        return self._public_query(
            QUERIES.get("public_events.graphql"),
            {
                "ids": list(event_ids),
            },
        )

    def fetch_club(self, club_id: str) -> dict[str, Any]:
        return self._private_query(
            QUERIES.get("club.graphql"),
            {"clubId": club_id},
        )

    def fetch_archived_meetups(
        self,
        club_id: str,
        *,
        first: int,
        after: str | None,
        members_first: int,
    ) -> dict[str, Any]:
        variables: dict[str, Any] = {
            "first": first,
            "after": after,
            "membersFirst": members_first,
            "clubId": club_id,
        }
        return self._private_query(
            QUERIES.get("archived_meetups.graphql"),
            variables,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _private_query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        token = self._get_token()
        if not token:
            raise CampfireError("Campfire token provider did not return a token")
        return self._graphql(PRIVATE_ENDPOINT, query, variables, token)

    def _public_query(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        return self._graphql(PUBLIC_ENDPOINT, query, variables, None)

    def _graphql(
        self,
        url: str,
        query: str,
        variables: dict[str, Any],
        token: str | None,
    ) -> dict[str, Any]:
        self.rate_limiter.acquire()
        body = json.dumps({"query": query, "variables": variables})
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(url, data=body, headers=headers, timeout=60)
            except requests.RequestException as exc:
                logger.warning("Campfire request failed", exc_info=exc)
                if attempt + 1 == self.config.max_retries:
                    raise CampfireRetryError("Campfire request failed") from exc
                time.sleep(1)
                continue

            if response.status_code == 429:
                raise CampfireRateLimitError("Too many requests")
            if response.status_code == 502:
                if attempt + 1 == self.config.max_retries:
                    raise CampfireRetryError("Bad gateway from Campfire")
                time.sleep(1)
                continue
            if response.status_code != 200:
                raise CampfireError(
                    f"Campfire request failed with status {response.status_code}: {response.text}"
                )

            payload = response.json()
            errors = [GraphQLError.from_dict(err) for err in payload.get("errors", [])]
            if errors:
                for err in errors:
                    logger.error("Campfire GraphQL error", extra={"error": err.message})
            return payload.get("data", {})

        raise CampfireRetryError("Too many retries")

    def _get_token(self) -> str | None:
        if not self.token_provider:
            return None
        return self.token_provider()


def build_graphql_data_source(
    *,
    config: CampfireConfig | None = None,
    token_provider: TokenProvider | None = None,
    session: requests.Session | None = None,
) -> GraphQLCampfireDataSource:
    """Factory helper to build the default data source."""
    return GraphQLCampfireDataSource(
        config=config,
        token_provider=token_provider,
        session=session,
    )
