"""Tests for API endpoints — health check and integration API responses."""

import pytest
from fastapi.testclient import TestClient


def _get_client():
    """Get a test client for the app."""
    from main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        client = _get_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "people-help"


class TestRootRedirect:
    def test_root_redirects_to_people_help(self):
        client = _get_client()
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/people-help"


class TestIntegrationAPIEndpoints:
    """Test integration API endpoints that don't require Supabase."""

    def test_workday_search(self):
        client = _get_client()
        resp = client.get("/integrations/workday/employees?q=alice")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "workday_mock"
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "Alice Chen"

    def test_workday_search_empty_query(self):
        client = _get_client()
        resp = client.get("/integrations/workday/employees?q=")
        # FastAPI query validation will return 422 for empty required param
        assert resp.status_code in (400, 422)

    def test_workday_employee_detail(self):
        client = _get_client()
        resp = client.get("/integrations/workday/employees/WD-1001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["employee"]["name"] == "Alice Chen"

    def test_workday_employee_not_found(self):
        client = _get_client()
        resp = client.get("/integrations/workday/employees/WD-9999")
        assert resp.status_code == 404

    def test_workday_org_chart(self):
        client = _get_client()
        resp = client.get("/integrations/workday/org-chart/WD-1002")
        assert resp.status_code == 200
        data = resp.json()
        assert data["employee"]["name"] == "Bob Martinez"
        assert len(data["direct_reports"]) >= 1

    def test_greenhouse_list_open_reqs(self):
        client = _get_client()
        resp = client.get("/integrations/greenhouse/requisitions?status=open")
        assert resp.status_code == 200
        data = resp.json()
        assert data["source"] == "greenhouse_mock"
        assert data["count"] == 3

    def test_greenhouse_req_detail(self):
        client = _get_client()
        resp = client.get("/integrations/greenhouse/requisitions/GH-401")
        assert resp.status_code == 200
        data = resp.json()
        assert data["requisition"]["title"] == "Senior Backend Engineer"
        assert len(data["candidates"]) == 3

    def test_greenhouse_req_not_found(self):
        client = _get_client()
        resp = client.get("/integrations/greenhouse/requisitions/GH-999")
        assert resp.status_code == 404


class TestChatEndpointValidation:
    """Test Pydantic validation on the chat endpoint (without hitting the LLM)."""

    def test_empty_body_rejected(self):
        client = _get_client()
        resp = client.post("/people-help/chat", json={})
        assert resp.status_code == 422  # Pydantic validation error

    def test_empty_message_rejected(self):
        client = _get_client()
        resp = client.post("/people-help/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_oversized_message_rejected(self):
        client = _get_client()
        resp = client.post("/people-help/chat", json={"message": "x" * 2001})
        assert resp.status_code == 422

    def test_invalid_json_rejected(self):
        client = _get_client()
        resp = client.post(
            "/people-help/chat",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422
