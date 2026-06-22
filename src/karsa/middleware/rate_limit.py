"""Rate limiting middleware -- Phase-4.

Simple in-memory rate limiter using sliding window.
Production: use Redis-backed rate limiter.
"""

import time
from collections import defaultdict
from typing import Dict, List

from fastapi import Request
from fastapi.responses import JSONResponse


class RateLimiter:
    """Sliding window rate limiter.

    Tracks request timestamps per client IP.
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        """Check if a request from client_ip is allowed."""
        now = time.time()
        window_start = now - self._window_seconds

        # Clean old entries
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip]
            if ts > window_start
        ]

        if len(self._requests[client_ip]) >= self._max_requests:
            return False

        self._requests[client_ip].append(now)
        return True

    def get_remaining(self, client_ip: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - self._window_seconds
        recent = [
            ts for ts in self._requests.get(client_ip, [])
            if ts > window_start
        ]
        return max(0, self._max_requests - len(recent))


# Default rate limiter: 100 requests per minute
_default_limiter = RateLimiter(max_requests=100, window_seconds=60)


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware.

    Returns 429 when rate limit exceeded.
    Adds X-RateLimit-Remaining header to responses.
    """
    client_ip = request.client.host if request.client else "unknown"

    if not _default_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "RATE_LIMITED",
                "message": f"Rate limit exceeded. Max {_default_limiter._max_requests} requests per {_default_limiter._window_seconds}s.",
            },
        )

    response = await call_next(request)
    remaining = _default_limiter.get_remaining(client_ip)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Limit"] = str(_default_limiter._max_requests)
    return response
