"""Tests for auth and rate-limiting middleware."""

import os
import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from middleware.auth import APIKeyMiddleware, _is_public
from middleware.rate_limit import RateLimitMiddleware, _requests


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------


def _make_auth_app(api_key: str = "test-secret"):
    """Create a minimal FastAPI app with auth middleware for testing."""
    app = FastAPI()
    with patch.dict(os.environ, {"API_KEY": api_key}):
        # Reimport to pick up new env
        import middleware.auth as auth_mod
        auth_mod.API_KEY = api_key
    app.add_middleware(APIKeyMiddleware)

    @app.get("/")
    async def root():
        return JSONResponse({"ok": True})

    @app.get("/people-help")
    async def page():
        return JSONResponse({"page": True})

    @app.post("/people-help/chat")
    async def chat():
        return JSONResponse({"chat": True})

    @app.get("/health")
    async def health():
        return JSONResponse({"status": "ok"})

    return app


class TestAuthMiddleware:
    def test_public_page_no_auth_needed(self):
        app = _make_auth_app("secret123")
        client = TestClient(app)
        # GET /people-help is a public UI page
        resp = client.get("/people-help")
        assert resp.status_code == 200

    def test_api_endpoint_requires_key(self):
        app = _make_auth_app("secret123")
        client = TestClient(app)
        resp = client.post("/people-help/chat", json={"message": "hi"})
        assert resp.status_code == 401
        assert "API key" in resp.json()["error"]

    def test_api_endpoint_with_valid_key(self):
        app = _make_auth_app("secret123")
        client = TestClient(app)
        resp = client.post(
            "/people-help/chat",
            json={"message": "hi"},
            headers={"X-API-Key": "secret123"},
        )
        assert resp.status_code == 200

    def test_api_endpoint_with_wrong_key(self):
        app = _make_auth_app("secret123")
        client = TestClient(app)
        resp = client.post(
            "/people-help/chat",
            json={"message": "hi"},
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_demo_mode_no_auth(self):
        """When API_KEY is empty, all endpoints are accessible."""
        app = _make_auth_app("")
        client = TestClient(app)
        resp = client.post("/people-help/chat", json={"message": "hi"})
        assert resp.status_code == 200


class TestIsPublic:
    """Test the path classification logic."""

    def test_static_is_public(self):
        from starlette.testclient import TestClient
        from fastapi import FastAPI, Request

        app = FastAPI()

        @app.get("/static/style.css")
        async def css():
            return "ok"

        # Create a mock request-like test
        # We test the function directly instead
        class FakeRequest:
            def __init__(self, method, path):
                self.method = method
                self.url = type("U", (), {"path": path})()

        assert _is_public(FakeRequest("GET", "/static/file.js"))
        assert _is_public(FakeRequest("GET", "/people-help"))
        assert _is_public(FakeRequest("GET", "/knowledge"))
        assert _is_public(FakeRequest("GET", "/workflows/run/some-id"))
        assert not _is_public(FakeRequest("POST", "/people-help/chat"))
        assert not _is_public(FakeRequest("POST", "/workflows/approvals/id/decide"))


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def setup_method(self):
        """Clear rate limit state before each test."""
        _requests.clear()

    def test_allows_requests_under_limit(self):
        import middleware.rate_limit as rl_mod
        old_limit = rl_mod.RATE_LIMIT
        rl_mod.RATE_LIMIT = 5

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.post("/people-help/chat")
        async def chat():
            return JSONResponse({"ok": True})

        client = TestClient(app)
        for _ in range(5):
            resp = client.post("/people-help/chat", json={})
            assert resp.status_code == 200

        rl_mod.RATE_LIMIT = old_limit

    def test_blocks_after_limit(self):
        import middleware.rate_limit as rl_mod
        old_limit = rl_mod.RATE_LIMIT
        rl_mod.RATE_LIMIT = 3

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.post("/people-help/chat")
        async def chat():
            return JSONResponse({"ok": True})

        client = TestClient(app)
        for _ in range(3):
            client.post("/people-help/chat", json={})

        # 4th request should be rate limited
        resp = client.post("/people-help/chat", json={})
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

        rl_mod.RATE_LIMIT = old_limit

    def test_non_llm_paths_not_limited(self):
        import middleware.rate_limit as rl_mod
        old_limit = rl_mod.RATE_LIMIT
        rl_mod.RATE_LIMIT = 1

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.post("/integrations/webhooks/test")
        async def webhook():
            return JSONResponse({"ok": True})

        client = TestClient(app)
        for _ in range(5):
            resp = client.post("/integrations/webhooks/test", json={})
            assert resp.status_code == 200

        rl_mod.RATE_LIMIT = old_limit

    def test_get_requests_not_limited(self):
        import middleware.rate_limit as rl_mod
        old_limit = rl_mod.RATE_LIMIT
        rl_mod.RATE_LIMIT = 1

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)

        @app.get("/people-help/chat")
        async def chat_get():
            return JSONResponse({"ok": True})

        client = TestClient(app)
        for _ in range(5):
            resp = client.get("/people-help/chat")
            assert resp.status_code == 200

        rl_mod.RATE_LIMIT = old_limit
