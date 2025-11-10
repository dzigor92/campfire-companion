from __future__ import annotations

import re
from typing import Literal


class ClubLookupError(ValueError):
    """Raised when the club lookup input cannot be uniquely resolved."""


CLUB_URL_REGEX = re.compile(
    r"https://campfire\.onelink\.me/[a-zA-Z0-9]+(?:\?[^ \t\r\n]*)?"
)


def extract_club_reference(raw: str | None) -> tuple[str | None, str | None]:
    """
    Scan the provided text for a club deep-link or UUID.

    Rules:
    - split on whitespace
    - prefer the first campfire.onelink URL if present
    - otherwise fall back to tokens with 4 hyphens (UUID heuristic)
    - error when multiple candidates are present
    """
    raw = (raw or "").strip()
    if not raw:
        return None, None

    club_url: str | None = None
    club_id: str | None = None
    for token in raw.split():
        match = CLUB_URL_REGEX.search(token)
        if match:
            if club_url or club_id:
                raise ClubLookupError("Multiple club URLs or IDs found.")
            club_url = match.group(0)
            continue

        if token.count("-") == 4:
            if club_url or club_id:
                raise ClubLookupError("Multiple club URLs or IDs found.")
            club_id = token

    return club_url, club_id


def normalize_club_lookup(
    raw: str | None,
    *,
    strict: bool = False,
    default_kind: Literal["url", "id", None] = None,
) -> tuple[str | None, str | None]:
    """
    Normalize raw user input into either a Campfire club URL or ID.

    When strict, the input must contain a resolvable reference (used for the
    combined tracker-style field). Otherwise we optionally fall back to the
    raw string so legacy ?url=/?id= parameters continue to work.
    """
    raw = (raw or "").strip()
    if not raw:
        if strict:
            raise ClubLookupError("No club reference provided.")
        return None, None

    club_url, club_id = extract_club_reference(raw)
    if club_url or club_id:
        return club_url, club_id

    if strict:
        raise ClubLookupError("No club URL or ID found in the provided input.")

    if default_kind == "url":
        return raw, None
    if default_kind == "id":
        return None, raw
    return None, None
