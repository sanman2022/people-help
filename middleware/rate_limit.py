"""In-memory rate limiter for LLM-calling endpoints.

No Redis dependency — uses a sliding window counter per IP.
Configurable via RATE_LIMIT_PER_MINUTE env var (default: 20).
"""

import logging
import os
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "20"))
WINDOW_SECONDS = 60

# Paths that call the LLM (expensive endpoints)
LLM_PATHS = {"/people-help/chat", "/people-help", "/knowledge/ask"}

# In-memory store: {ip: [timestamp, ...]}
_requests: dict[str, list[float]] = defaultdict(list)


def _cleanup(ip: str, now: float) -> None:
    """Remove timestamps older than the window."""
    cutoff = now - WINDOW_SECONDS
    _requests[ip] = [t for t in _requests[ip] if t > cutoff]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate-limit LLM-calling endpoints per client IP."""

    async def dispatch(self, request: Request, call_next):
        if RATE_LIMIT <= 0:
            return await call_next(request)

        path = request.url.path
        if request.method != "POST" or path not in LLM_PATHS:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        _cleanup(ip, now)

        if len(_requests[ip]) >= RATE_LIMIT:
            retry_after = int(WINDOW_SECONDS - (now - _requests[ip][0])) + 1
            logger.warning("Rate limit hit for %s on %s (%d requests)", ip, path, len(_requests[ip]))
            return JSONResponse(
                {"error": "Rate limit exceeded. Try again shortly.", "retry_after_seconds": retry_after},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        _requests[ip].append(now)
        return await call_next(request)
