"""A judge that runs out of room must say so, not 502.

Found in production on 2026-08-20, after the Gateway API route timeout (charts
!143 + welance-prod !13) removed the 15s cut that had been hiding it. With the
timeout gone the LLM judge ran to completion and *still* failed — this time at
1569 characters, mid-string, on `json.decoder.JSONDecodeError: Unterminated
string`. The answer was not slow, it was cut: fourteen verdicts, each with a
verbatim quote, do not fit in `llm_max_tokens = 1500`, and a brief written in a
non-Latin script needs more tokens per character still.

Two failures in one, and this file pins both:

- the ceiling was too low for the ruleset the service actually ships;
- hitting the ceiling produced `502 the judge upstream failed`, which points
  the reader at the model provider when the truth is a local setting. The
  provider did answer, and it told us it had stopped early: `finish_reason:
  "length"`. Nothing read it.

The score must never be computed from a truncated answer. Missing verdicts fall
back to `not_applicable`, which silently *changes the number* — a wrong score
is worse than a refusal.
"""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

BRIEF = "# Portal\nProblem: bookings by phone. Users: dispatchers. Budget 120000 EUR."

# fourteen verdicts start fine and stop mid-quote, exactly as the model left it
TRUNCATED = (
    '[{"rule_id":"clear-title","status":"pass","confidence":0.9,"quote":"Portal","note":"named"},'
    '{"rule_id":"problem-defined","status":"pass","confidence":0.9,"quote":"bookings by ph'
)

COMPLETE = '[{"rule_id":"clear-title","status":"pass","confidence":0.9,"quote":"Portal","note":"ok"}]'


@pytest.fixture
def openrouter(monkeypatch):
    """Answer as OpenRouter does, including the finish_reason nobody was reading."""
    state = {"content": TRUNCATED, "finish_reason": "length"}

    def handler(request: httpx.Request) -> httpx.Response:
        state["last_body"] = request.content.decode()
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": state["content"]},
                        "finish_reason": state["finish_reason"],
                    }
                ]
            },
        )

    class _MockedClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", _MockedClient)
    return state


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "sk-or-v1-test")
    from app.settings import settings

    settings.cache_clear()
    yield TestClient(app, raise_server_exceptions=False)
    settings.cache_clear()


def test_a_cut_off_answer_is_reported_as_such_not_as_an_upstream_failure(client, openrouter):
    r = client.post("/v1/score", json={"brief": BRIEF, "judge": "llm"})
    assert r.status_code == 503, f"expected an honest 503, got {r.status_code}: {r.text[:200]}"
    detail = r.json()["detail"].lower()
    assert "cut" in detail or "truncat" in detail, detail
    # the reader must be pointed at the ceiling, not at the provider
    assert "upstream" not in detail


def test_a_truncated_answer_never_becomes_a_score(client, openrouter):
    r = client.post("/v1/score", json={"brief": BRIEF, "judge": "llm"})
    assert "score" not in r.json(), "a partial answer must not be scored"


def test_a_complete_answer_still_scores(client, openrouter):
    openrouter["content"] = COMPLETE
    openrouter["finish_reason"] = "stop"
    r = client.post("/v1/score", json={"brief": BRIEF, "judge": "llm"})
    assert r.status_code == 200, r.text[:300]
    assert "score" in r.json()


def test_the_ceiling_fits_the_ruleset_this_service_ships():
    """Fourteen verdicts with verbatim quotes, with room for a non-Latin script."""
    import perfect_brief
    from app.settings import settings

    settings.cache_clear()
    rules, _ = perfect_brief.load_bundled()
    floor = 200 * len(rules)
    assert settings().llm_max_tokens >= floor, (
        f"{len(rules)} rules need room for a quote and a note each; "
        f"{settings().llm_max_tokens} tokens is below the {floor} floor"
    )


def test_the_judge_asks_for_short_reasoning_since_it_is_billed_from_the_ceiling(client, openrouter):
    """Extraction, not deliberation — and thinking is spent before any JSON."""
    openrouter["content"] = COMPLETE
    openrouter["finish_reason"] = "stop"
    client.post("/v1/score", json={"brief": BRIEF, "judge": "llm"})
    sent = json.loads(openrouter["last_body"])
    assert sent.get("reasoning") == {"effort": "low"}, sent.get("reasoning")
