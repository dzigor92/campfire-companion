"""Campfire-specific exception hierarchy."""


class CampfireError(Exception):
    """Base error for Campfire client failures."""


class CampfireRateLimitError(CampfireError):
    """Raised when Campfire returns HTTP 429."""


class CampfireRetryError(CampfireError):
    """Raised when Campfire keeps failing after retries."""


class CampfireUnsupportedMeetup(CampfireError):
    """Raised when attempting to resolve unsupported meetup types."""


class CampfireEventNotFound(CampfireError):
    """Raised when a referenced event cannot be found via public APIs."""
