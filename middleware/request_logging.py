"""Request logging middleware — structured log lines with timing and request IDs."""

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("people_help.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status, and duration for every request.
    Attaches a unique request_id for tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # Skip noisy static asset logs
        path = request.url.path
        if path.startswith("/static"):
            return response

        logger.info(
            "[%s] %s %s -> %d (%.1fms)",
            request_id,
            request.method,
            path,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
