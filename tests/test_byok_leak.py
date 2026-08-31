"""The canary: a caller's own key must reach exactly one destination.

`site/security.html` tells readers not to trust its prose and to read this file
instead. So this is not a unit test of a helper — it drives every endpoint that
accepts `X-LLM-Key` with a sentinel key and then hunts that sentinel through
every channel the service can emit on: log records, raw stdout/stderr, the
response body, response headers, and everything handed to Redis.

Two things this deliberately does NOT do, because they would weaken it:

- It does not patch `llm_client.complete`. The header construction is the code
  under test, so the interception happens at the transport.
- It does not only watch `logging`. The most likely accidental leak is a bare
  `print()` during debugging, which no log-record assertion can see — hence
  `capfd` alongside `caplog`.

The point is not that today's code is clean (it is). The point is that the
well-meaning debug line someone adds in a year turns this red.
"""

from __future__ import annotations

import json
import logging

import httpx
import pytest

from app import cache, llm_client
from brief_bar import load_bundled

# Distinctive enough that a substring search cannot produce a false negative,
# and shaped like the real thing so no code path treats it as special.
CANARY = "sk-or-v1-CANARYcanary0000deadbeef0000cafebabe0000"

BRIEF = "# T\nProblem: x. Budget 15k."

_RULES, _ = load_bundled()
VERDICTS = json.dumps(
    [
        {"rule_id": rid, "status": "fail", "confidence": 0.9, "quote": "", "note": "n"}
        for rid in _RULES
    ]
)
SUGGESTIONS = '[{"rule_id":"clear-title","text":"A title naming the product and the outcome."}]'
REVIEW = '[{"id":"clear-title","accepted":true,"reason":"satisfies the rule"}]'

# every endpoint that accepts the header, not just the one we thought of first
ENDPOINTS = [
    ("/v1/score", {"brief": BRIEF, "judge": "llm"}),
    ("/v1/suggest", {"brief": BRIEF, "rule_id": "clear-title", "locale": "en-GB"}),
    ("/v1/suggest/all", {"brief": BRIEF, "rule_ids": ["clear-title"], "locale": "en-GB"}),
]


@pytest.fixture
def outbound(monkeypatch):
    """Intercept at the transport, and answer in the shape each prompt expects."""
    calls: list[dict] = []
    state: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.content.decode()
        calls.append({"headers": dict(request.headers), "url": str(request.url), "body": body})
        if state.get("respond_with", 200) != 200:
            return httpx.Response(state["respond_with"], json={"error": {"message": "no credit"}})
        if "skeptical reviewer" in body:
            content = REVIEW
        elif "You are improving" in body:
            content = SUGGESTIONS
        else:
            content = VERDICTS
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    class _MockedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _MockedClient)
    state["calls"] = calls
    return state


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


def assert_no_leak(response, redis_writes, caplog, capfd):
    """The sentinel may live in exactly one place, and this is not it."""
    assert CANARY not in response.text
    assert CANARY not in str(dict(response.headers))

    for key, value in redis_writes:
        assert CANARY not in key, f"key material in a cache key: {key}"
        assert CANARY not in str(value), f"key material in a cached value under {key}"

    for record in caplog.records:
        assert CANARY not in record.getMessage()
        assert CANARY not in str(record.args or "")
        assert CANARY not in caplog.handler.format(record)

    # a bare print() is the likeliest accidental leak and no log assertion sees it
    captured = capfd.readouterr()
    assert CANARY not in captured.out, "key written to stdout"
    assert CANARY not in captured.err, "key written to stderr"


@pytest.mark.parametrize("path,body", ENDPOINTS, ids=lambda v: v if isinstance(v, str) else "")
def test_byok_key_reaches_only_the_provider(
    client, outbound, redis_writes, caplog, capfd, path, body
):
    caplog.set_level(logging.DEBUG)

    r = client.post(path, json=body, headers={"x-llm-key": CANARY})
    assert r.status_code == 200, r.text

    # It must arrive where it is meant to: the provider, as a bearer token.
    assert outbound["calls"], f"{path} never called the provider"
    for call in outbound["calls"]:
        assert call["headers"]["authorization"] == f"Bearer {CANARY}"
        assert call["url"] == llm_client.OPENROUTER_URL
        assert CANARY not in call["body"], "the key must not ride in the request body"

        payload = json.loads(call["body"])
        is_suggestion_generation = "You are improving" in call["body"]
        if is_suggestion_generation:
            assert payload["provider"] == {"sort": "latency"}
        else:
            assert "provider" not in payload

    assert_no_leak(r, redis_writes, caplog, capfd)


@pytest.mark.parametrize("path,body", ENDPOINTS, ids=lambda v: v if isinstance(v, str) else "")
def test_byok_key_absent_from_the_error_path(
    client, outbound, redis_writes, caplog, capfd, path, body
):
    """Error paths echo exception text — the likeliest place for a secret to slip out."""
    caplog.set_level(logging.DEBUG)
    outbound["respond_with"] = 401  # provider rejects the key

    r = client.post(path, json=body, headers={"x-llm-key": CANARY})
    assert r.status_code >= 400

    assert_no_leak(r, redis_writes, caplog, capfd)
