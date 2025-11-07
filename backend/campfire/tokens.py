from __future__ import annotations

from typing import Protocol


class TokenProvider(Protocol):
    def __call__(self) -> str | None:
        ...
