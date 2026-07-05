"""Test setup: force the mock judge, point Redis at nothing (it degrades), no rate limit."""

import os

os.environ.setdefault("PB_DEFAULT_JUDGE", "mock")
os.environ.setdefault("PB_ANTHROPIC_API_KEY", "")
os.environ.setdefault("PB_REDIS_URL", "redis://127.0.0.1:6390/0")  # unreachable on purpose
os.environ.setdefault("PB_RATE_LIMIT_PER_MINUTE", "0")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
