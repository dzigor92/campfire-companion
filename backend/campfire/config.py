from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(slots=True)
class CampfireConfig:
    """Runtime configuration mirroring the Go client."""

    every: timedelta = timedelta(seconds=1)
    burst: int = 40
    max_retries: int = 3

    def __post_init__(self) -> None:
        if self.every <= timedelta(0):
            raise ValueError("Rate limiter interval must be positive")
        if self.burst <= 0:
            raise ValueError("Burst must be positive")
        if self.max_retries <= 0:
            raise ValueError("max_retries must be positive")


def default_config() -> CampfireConfig:
    return CampfireConfig()
