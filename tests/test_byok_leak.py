"""The canary: a caller's own key must reach exactly one destination.

`site/security.html` tells readers not to trust its prose and to read this file
instead. So this is not a unit test of a helper — it drives a real `/v1/score`
request with a sentinel key and then hunts that sentinel through every channel
the service can emit on: log records, the response body, response headers, and
everything handed to Redis.

The point is not that today's code is clean (it is). The point is that the
well-meaning `log.debug(headers)` someone adds in a year turns this red.
"""

from __future__ import annotations

import logging

import httpx
import pytest

from app import cache, llm_client

# Distinctive enough that a substring search cannot produce a false negative,
# and shaped like the real thing so no code path treats it as special.
CANARY = "sk-or-v1-CANARYcanary0000deadbeef0000cafebabe0000"

VERDICTS = '[{"rule_id":"clear-title","status":"pass","confidence":0.9,"quote":"t","note":""}]'
BRIEF = {"brief": "# T\nProblem: x. Budget 15k.", "judge": "llm"}


@pytest.fixture
def outbound(monkeypatch):
    """Intercept at the transport, so the real `complete()` builds the header.

    Patching `llm_client.complete` would prove nothing — the header
    construction is the code under test.
    """
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["url"] = str(request.url)
        seen["body"] = request.content.decode()
        status = seen.get("respond_with", 200)
        if status != 200:
            return httpx.Response(status, json={"error": {"message": "no credit"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": VERDICTS}}]})

    class _MockedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _MockedClient)
    return seen


@pytest.fixture
def redis_writes(monkeypatch):
    """Capture everything offered to Redis — keys and values both."""
    writes: list[tuple[str, object]] = []

    async def fake_set(key, value, ttl):
        writes.append((key, value))

    async def fake_get(key):
        writes.append((key, None))
        return None

    monkeypatch.setattr(cache, "set_json", fake_set)
    monkeypatch.setattr(cache, "get_json", fake_get)
    return writes


def test_byok_key_reaches_only_the_provider(client, outbound, redis_writes, caplog):
    caplog.set_level(logging.DEBUG)

    r = client.post("/v1/score", json=BRIEF, headers={"x-llm-key": CANARY})
    assert r.status_code == 200, r.text

    # It must arrive where it is meant to: the provider, as a bearer token.
    assert outbound["headers"]["authorization"] == f"Bearer {CANARY}"
    assert outbound["url"] == llm_client.OPENROUTER_URL

    # ...and nowhere else.
    assert CANARY not in r.text
    assert CANARY not in str(dict(r.headers))
    assert CANARY not in outbound["body"], "the key must not ride in the request body"

    for key, value in redis_writes:
        assert CANARY not in key, f"key material in a cache key: {key}"
        assert CANARY not in str(value), f"key material in a cached value under {key}"

    for record in caplog.records:
        assert CANARY not in record.getMessage()
        assert CANARY not in str(record.args or "")
        assert CANARY not in caplog.handler.format(record)


def test_byok_key_absent_from_the_error_path(client, outbound, redis_writes, caplog):
    """The 502 handler echoes exception text. Prove the exception is clean."""
    caplog.set_level(logging.DEBUG)
    outbound["respond_with"] = 401  # provider rejects the key

    r = client.post("/v1/score", json=BRIEF, headers={"x-llm-key": CANARY})
    assert r.status_code == 502
    assert "judge error" in r.json()["detail"]

    # httpx's HTTPStatusError carries status and URL, never headers.
    assert CANARY not in r.text
    # log.exception() prints a traceback: source lines, not local values.
    for record in caplog.records:
        assert CANARY not in caplog.handler.format(record)
