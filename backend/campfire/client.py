"""GraphQL client for interacting with the Campfire backend (events, clubs, meetups)."""

from __future__ import annotations

import base64
import logging
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

from .config import CampfireConfig
from .datasource import CampfireDataSource, build_graphql_data_source
from .exceptions import CampfireError, CampfireEventNotFound, CampfireUnsupportedMeetup
from .models import Club, Events, Event
from .tokens import TokenProvider

logger = logging.getLogger(__name__)

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


class CampfireClient:
    """Campfire GraphQL client exposing high-level helpers (resolve_event, get_club, etc.)."""

    def __init__(
        self,
        config: CampfireConfig | None = None,
        token_provider: TokenProvider | None = None,
        session: Any | None = None,
        data_source: CampfireDataSource | None = None,
    ) -> None:
        self._data_source = data_source or self._build_default_data_source(
            config=config,
            token_provider=token_provider,
            session=session,
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def resolve_short_url(self, url: str) -> str:
        final_url, response_body = self._data_source.resolve_short_url(url)
        if any(final_url.startswith(prefix) for prefix in VALID_MEETUP_PREFIXES):
            return final_url
        match = MEETUP_URL_REGEX.search(response_body)
        if not match:
            raise CampfireError("Short URL did not contain a meetup link")
        return match.group(0)

    def resolve_event_id(self, meetup_url: str) -> str:
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
            match = next(
                (item for item in events.public_map_objects_by_id if item.map_object_id == public_id),
                None,
            )
            if not match:
                raise CampfireError(
                    f"Event id mismatch: expected {public_id}, got {[item.map_object_id for item in events.public_map_objects_by_id]}"
                )
            campfire_event_id = match.event_id
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
        payload = self._data_source.fetch_event(event_id)
        return Event.from_dict(payload["event"])

    def get_events(self, event_ids: Iterable[str]) -> Events:
        payload = self._data_source.fetch_public_events(event_ids)
        return Events.from_dict(payload)

    def get_club(self, club_id: str) -> Club:
        payload = self._data_source.fetch_club(club_id)
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
            payload = self._data_source.fetch_archived_meetups(
                club_id,
                first=50,
                after=cursor,
                members_first=100000000,
            )
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
    def _build_default_data_source(
        self,
        config: CampfireConfig | None,
        token_provider: TokenProvider | None,
        session: any | None,
    ) -> CampfireDataSource:
        return build_graphql_data_source(
            config=config,
            token_provider=token_provider,
            session=session,
        )
