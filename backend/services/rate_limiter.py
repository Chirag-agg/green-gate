"""In-memory rate limiting utilities for FastAPI routes."""

from collections import deque
from threading import Lock
from time import time

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Simple per-key fixed-window limiter using in-memory storage."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str) -> int | None:
        """Check and record a request event.

        Returns seconds to wait if limited, otherwise None.
        """
        now = time()
        with self._lock:
            events = self._events.setdefault(key, deque())
            window_start = now - self.window_seconds

            while events and events[0] <= window_start:
                events.popleft()

            if len(events) >= self.max_requests:
                retry_after = int(events[0] + self.window_seconds - now) + 1
                return max(retry_after, 1)

            events.append(now)
            return None


def rate_limit(scope: str, max_requests: int, window_seconds: int):
    """Create a FastAPI dependency enforcing per-IP route limits."""
    limiter = InMemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)

    async def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"{scope}:{client_ip}"
        retry_after = limiter.check(key)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
