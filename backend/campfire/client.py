from __future__ import annotations

import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional
from urllib.parse import ParseResult, parse_qs, urlparse

import requests

from .config import CampfireConfig, default_config
from .models import Club, Events, Event, GraphQLError
from .rate_limiter import RateLimiter
from .tokens import TokenProvider

logger = logging.getLogger(__name__)

PUBLIC_ENDPOINT = "https://niantic-social-api.nianticlabs.com/public/graphql"
PRIVATE_ENDPOINT = "https://niantic-social-api.nianticlabs.com/graphql"

MEETUP_SHORT_PREFIX = "https://cmpf.re/"
PUBLIC_MEETUP_PREFIX = "https://niantic-social.nianticlabs.com/public/meetup/"
PUBLIC_MEETUP_WITHOUT_LOCATION_PREFIX = (
    "https://niantic-social.nianticlabs.com/public/meetup-without-location/"
)
DISCOVER_MEETUP_PREFIX = "https://campfire.nianticlabs.com/discover/meetup/"

MEETUP_URL_REGEX = re.compile(
    r"https://(?:niantic-social\.nianticlabs\.com/public/meetup(?:-without-location)?|campfire\.nianticlabs\.com/discover/meetup)/[a-zA-Z0-9-]+"
)
VALID_MEETUP_PREFIXES = (
    PUBLIC_MEETUP_PREFIX,
    PUBLIC_MEETUP_WITHOUT_LOCATION_PREFIX,
    DISCOVER_MEETUP_PREFIX,
)


class CampfireError(Exception):
    pass


class CampfireRateLimitError(CampfireError):
    pass


class CampfireRetryError(CampfireError):
    pass


class CampfireUnsupportedMeetup(CampfireError):
    pass


class CampfireEventNotFound(CampfireError):
    pass


def _load_query(name: str) -> str:
    path = Path(__file__).with_suffix("")
    query_path = Path(__file__).parent / "queries" / name
    return query_path.read_text(encoding="utf-8")


EVENT_QUERY = _load_query("event.graphql")
PUBLIC_EVENTS_QUERY = _load_query("public_events.graphql")
ARCHIVED_MEETUPS_QUERY = _load_query("archived_meetups.graphql")
CLUB_QUERY = _load_query("club.graphql")


class CampfireClient:
    """Feature-parity port of the Go GraphQL client."""

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

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def resolve_short_url(self, url: str) -> str:
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        final_url = response.url
        if any(final_url.startswith(prefix) for prefix in VALID_MEETUP_PREFIXES):
            return final_url
        match = MEETUP_URL_REGEX.search(response.text)
        if not match:
            raise CampfireError("Short URL did not contain a meetup link")
        return match.group(0)

    def resolve_event_id(self, meetup_url: str) -> str:
        self.rate_limiter.acquire()

        original = meetup_url
        if meetup_url.startswith(MEETUP_SHORT_PREFIX):
            meetup_url = self.resolve_short_url(meetup_url)

        if meetup_url.startswith(PUBLIC_MEETUP_WITHOUT_LOCATION_PREFIX):
            raise CampfireUnsupportedMeetup("meetup without location is not supported")

        if meetup_url.startswith(DISCOVER_MEETUP_PREFIX):
            campfire_event_id = Path(meetup_url).name
        elif meetup_url.startswith(PUBLIC_MEETUP_PREFIX):
            public_id = Path(meetup_url).name
            if not public_id:
                raise CampfireError("Could not extract event id from URL")
            events = self.get_events([public_id])
            if not events.public_map_objects_by_id:
                raise CampfireEventNotFound(public_id)
            first = events.public_map_objects_by_id[0]
            if first.id != public_id:
                raise CampfireError(
                    f"Event id mismatch: expected {public_id}, got {first.id}"
                )
            campfire_event_id = first.event.id
        else:
            raise CampfireError(
                "Invalid meetup URL; expected niantic-social, cmpf.re, or campfire discover link"
            )

        if not campfire_event_id:
            raise CampfireError(f"Invalid meetup URL: {original}")
        return campfire_event_id

    def resolve_event(self, meetup_url: str) -> Event:
        event_id = self.resolve_event_id(meetup_url)
        return self.get_event(event_id)

    def get_event(self, event_id: str) -> Event:
        payload = self._private_query(
            EVENT_QUERY,
            {
                "id": event_id,
                "first": 100000000,
            },
        )
        return Event.from_dict(payload["event"])

    def get_events(self, event_ids: Iterable[str]) -> Events:
        payload = self._public_query(
            PUBLIC_EVENTS_QUERY,
            {
                "ids": list(event_ids),
            },
        )
        return Events.from_dict(payload)

    def get_club(self, club_id: str) -> Club:
        payload = self._private_query(
            CLUB_QUERY,
            {
                "clubId": club_id,
            },
        )
        return Club.from_dict(payload["club"])

    def resolve_club(self, club_url: str) -> Club:
        club_id = self.resolve_club_id(club_url)
        return self.get_club(club_id)

    def resolve_club_id(self, club_url: str) -> str:
        parsed = urlparse(club_url)
        query = parse_qs(parsed.query)
        encoded = query.get("deep_link_sub1", [None])[0]
        if not encoded:
            raise CampfireError("No deep_link_sub1 parameter present")

        decoded = base64.b64decode(encoded).decode()
        values = parse_qs(decoded)
        if values.get("r", [None])[0] != "clubs":
            raise CampfireError("Decoded link is not a club deep-link")
        club_id = values.get("c", [None])[0]
        if not club_id:
            raise CampfireError("Club id missing from deep-link payload")
        return club_id

    def get_past_meetups(self, club_id: str) -> list[Event]:
        cursor: str | None = None
        results: list[Event] = []
        while True:
            variables: dict[str, Any] = {
                "first": 50,
                "after": cursor,
                "membersFirst": 100000000,
                "clubId": club_id,
            }
            payload = self._private_query(ARCHIVED_MEETUPS_QUERY, variables)
            club = payload["club"]
            feed = club["archivedFeed"]
            for edge in feed.get("edges", []):
                if edge.get("node", {}).get("__typename") == "Event":
                    results.append(Event.from_dict(edge["node"]))
            page_info = feed.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
        return results

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
