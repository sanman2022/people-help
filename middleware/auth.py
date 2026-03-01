"""API key authentication middleware.

When API_KEY is set in env, protects /people-help/chat and API endpoints.
UI pages (HTML) remain accessible. Set API_KEY="" to disable for demo mode.
"""

import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

API_KEY = os.environ.get("API_KEY", "")

# Paths that never require auth (UI pages, health, static, seed)
PUBLIC_PREFIXES = ("/static", "/docs", "/openapi.json", "/favicon.ico")
PUBLIC_EXACT = {"/", "/people-help", "/knowledge", "/workflows", "/events",
                "/analytics", "/integrations", "/integrations/hiring",
                "/workflows/approvals"}


def _is_public(request: Request) -> bool:
    """Check if the path is a public UI page or asset."""
    path = request.url.path

    # Static / docs
    if any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return True

    # Exact UI page GETs
    if request.method == "GET" and path in PUBLIC_EXACT:
        return True

    # GET-based UI sub-pages (workflow run detail, seed endpoints)
    if request.method == "GET" and (
        path.startswith("/workflows/run/")
        or path.startswith("/knowledge/seed")
        or path.startswith("/workflows/definitions/seed")
        or path.startswith("/workflows/simulate")
    ):
        return True

    return False


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header on protected routes.

    Disabled when API_KEY env var is empty (demo mode).
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth if no key configured (demo mode)
        if not API_KEY:
            return await call_next(request)

        # Skip auth for public paths
        if _is_public(request):
            return await call_next(request)

        # Check header
        provided = request.headers.get("X-API-Key", "")
        if provided != API_KEY:
            logger.warning("Auth failed for %s %s from %s",
                           request.method, request.url.path, request.client.host if request.client else "unknown")
            return JSONResponse({"error": "Invalid or missing API key"}, status_code=401)

        return await call_next(request)
