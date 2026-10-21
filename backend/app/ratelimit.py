"""Small in-memory sliding-window limiter. Per process, which is enough for one machine."""

import time
from collections import defaultdict, deque

from fastapi import HTTPException


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_sweep = time.monotonic()

    def _sweep(self, now: float) -> None:
        # Drop keys with no hits inside the window, so unused keys do not pile up.
        stale = [key for key, hits in self._hits.items() if not hits or now - hits[-1] > self.window]
        for key in stale:
            del self._hits[key]
        self._last_sweep = now

    def _recent(self, key: str, now: float) -> deque[float]:
        if now - self._last_sweep > self.window:
            self._sweep(now)
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        return hits

    def ensure_allowed(self, key: str, message: str) -> None:
        """Raise 429 if the key has used its budget, without counting this call."""
        if len(self._recent(key, time.monotonic())) >= self.limit:
            raise HTTPException(status_code=429, detail=message)

    def record(self, key: str) -> None:
        now = time.monotonic()
        self._recent(key, now).append(now)

    def check(self, key: str, message: str) -> None:
        """Count this call, raising 429 when the budget is already used."""
        self.ensure_allowed(key, message)
        self.record(key)

    def reset(self) -> None:
        self._hits.clear()

    def __len__(self) -> int:
        return len(self._hits)
