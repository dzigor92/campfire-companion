from __future__ import annotations

import threading
import time
from datetime import timedelta


class RateLimiter:
    """A minimal token bucket implementation for sync code."""

    def __init__(self, every: timedelta, burst: int) -> None:
        self._interval = every.total_seconds()
        self._capacity = float(burst)
        self._tokens = float(burst)
        self._lock = threading.Lock()
        self._last = time.monotonic()

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self._capacity, self._tokens + elapsed / self._interval)
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
            time.sleep(self._interval / self._capacity)
