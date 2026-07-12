"""Fixed-window in-memory rate limiter for the login endpoint.

Keyed by client IP. Sufficient for a single-process deployment; swap for a
shared store (Redis) when running multiple workers.
"""

import time
from collections import defaultdict


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        self._hits[key] = [t for t in self._hits[key] if t > cutoff]
        if len(self._hits[key]) >= self.max_attempts:
            return False
        self._hits[key].append(now)
        return True
