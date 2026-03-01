"""Shared pytest fixtures for People Help tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client — imports app lazily to allow env patching."""
    from main import app
    return TestClient(app)
