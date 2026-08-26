"""The verifier loop, with llm_client.complete stubbed — no network.

The stub plays both roles: generation calls return suggestion JSON, review
calls (detected by the review prompt's marker) return verdicts scripted per
test. Redis is unreachable in tests, so the suggestion cache is inert.
"""

import asyncio
import json

import pytest

from app import scorer
from app.settings import settings

BRIEF = "Landing page for a Berlin bakery chain. Budget 12000 EUR, deadline October."


@pytest.fixture(autouse=True)
def llm_on(monkeypatch):
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PB_OPENROUTER_MODELS", "deepseek/deepseek-v4-pro,deepseek/deepseek-v4-flash")
    monkeypatch.setenv("PB_SUGGEST_MODEL", "deepseek/deepseek-v4-flash")
    monkeypatch.setenv("PB_VERIFIER_MODEL", "deepseek/deepseek-v4-flash")
    # Most tests below exercise the optional conservative verifier path. The
    # interactive production default is covered separately.
    monkeypatch.setenv("PB_SUGGEST_VERIFY", "true")

    async def cache_miss(key):
        return None

    async def ignore_cache(key, value, ttl):
        return None

    monkeypatch.setattr(scorer.cache, "get_json", cache_miss)
    monkeypatch.setattr(scorer.cache, "set_json", ignore_cache)
    settings.cache_clear()
    yield
    settings.cache_clear()


def _is_review(prompt: str) -> bool:
    return "SUGGESTIONS UNDER REVIEW" in prompt


def test_accept_first_pass(monkeypatch):
    calls = []

    async def stub(prompt, model=None, api_key=None, **kwargs):
        calls.append((model, _is_review(prompt), kwargs))
        if _is_review(prompt):
            return json.dumps([{"id": "budget-floor", "accepted": True, "reason": "cites 12000 EUR"}])
        return json.dumps([{"rule_id": "budget-floor", "text": "Budget is 12000 EUR, confirmed by finance."}])

    monkeypatch.setattr(scorer.llm_client, "complete", stub)
    out, meta = asyncio.run(scorer.suggest_all(BRIEF, ["budget-floor"], "en-GB", None, None))
    assert meta["screened"] is True
    assert meta["iterations"] == 1
    assert meta["verifier_model"] == "deepseek/deepseek-v4-flash"
    assert meta["cached"] is False
    assert out[0].review.accepted is True
    generation_call, review_call = calls
    assert generation_call == (
        "deepseek/deepseek-v4-flash",
        False,
        {"max_tokens": settings().suggest_all_max_tokens, "purpose": "suggest-all"},
    )
    assert review_call == (
        "deepseek/deepseek-v4-flash",
        True,
        {"max_tokens": settings().verifier_max_tokens, "purpose": "verify"},
    )


def test_reject_then_regenerate(monkeypatch):
    state = {"reviews": 0}

    async def stub(prompt, model=None, api_key=None, **kwargs):
        if _is_review(prompt):
            state["reviews"] += 1
            ok = state["reviews"] >= 2
            return json.dumps(
                [{"id": "budget-floor", "accepted": ok, "reason": "fixed" if ok else "generic"}]
            )
        if "PREVIOUS ATTEMPT REJECTED" in prompt:
            return json.dumps(
                [{"rule_id": "budget-floor", "text": "Second attempt names the 12000 EUR budget."}]
            )
        return json.dumps([{"rule_id": "budget-floor", "text": "Add a budget."}])

    monkeypatch.setattr(scorer.llm_client, "complete", stub)
    out, meta = asyncio.run(scorer.suggest_all(BRIEF, ["budget-floor"], "en-GB", None, None))
    assert meta["screened"] is True
    assert meta["iterations"] == 2
    assert "Second attempt" in out[0].text
    assert out[0].review.accepted is True


def test_best_effort_after_max_retries(monkeypatch):
    async def stub(prompt, model=None, api_key=None, **kwargs):
        if _is_review(prompt):
            return json.dumps([{"id": "budget-floor", "accepted": False, "reason": "still generic"}])
        return json.dumps([{"rule_id": "budget-floor", "text": "Add a budget."}])

    monkeypatch.setattr(scorer.llm_client, "complete", stub)
    out, meta = asyncio.run(scorer.suggest_all(BRIEF, ["budget-floor"], "en-GB", None, None))
    assert meta["screened"] is False
    assert meta["iterations"] == 3  # initial + 2 retries
    assert out[0].review.accepted is False
    assert out[0].review.reason == "still generic"


def test_reviewer_crash_degrades_gracefully(monkeypatch):
    async def stub(prompt, model=None, api_key=None, **kwargs):
        if _is_review(prompt):
            raise RuntimeError("provider down")
        return json.dumps([{"rule_id": "budget-floor", "text": "Budget is 12000 EUR."}])

    monkeypatch.setattr(scorer.llm_client, "complete", stub)
    out, meta = asyncio.run(scorer.suggest_all(BRIEF, ["budget-floor"], "en-GB", None, None))
    assert meta["screened"] is False
    assert out and out[0].review is None
    assert out[0].text == "Budget is 12000 EUR."


def test_single_rule_suggest_reviews_by_index(monkeypatch):
    async def stub(prompt, model=None, api_key=None, **kwargs):
        if _is_review(prompt):
            return json.dumps(
                [
                    {"id": "0", "accepted": True, "reason": "anchored"},
                    {"id": "1", "accepted": True, "reason": "anchored"},
                    {"id": "2", "accepted": False, "reason": "generic"},
                ]
            )
        return json.dumps(
            [
                {"label": "State the budget", "text": "Budget is 12000 EUR."},
                {"label": "Name the deadline", "text": "Deadline is end of October."},
                {"label": "Vague", "text": "Add more detail."},
            ]
        )

    monkeypatch.setattr(scorer.llm_client, "complete", stub)
    out, meta = asyncio.run(scorer.suggest(BRIEF, "budget-floor", "en-GB", None, None))
    assert len(out) == 3
    assert [s.review.accepted for s in out] == [True, True, False]
    assert meta["verifier_model"] == "deepseek/deepseek-v4-flash"


def test_single_rule_default_returns_after_generation(monkeypatch):
    monkeypatch.setenv("PB_SUGGEST_VERIFY", "false")
    settings.cache_clear()
    calls = []

    async def stub(prompt, model=None, api_key=None, **kwargs):
        calls.append(kwargs["purpose"])
        return json.dumps(
            [
                {"label": "State the budget", "text": "Budget is 12000 EUR."},
                {"label": "Name the deadline", "text": "Deadline is end of October."},
                {"label": "Name the users", "text": "Bakery managers use it daily."},
            ]
        )

    monkeypatch.setattr(scorer.llm_client, "complete", stub)
    out, meta = asyncio.run(scorer.suggest(BRIEF, "budget-floor", "en-GB", None, None))
    assert len(out) == 3
    assert calls == ["suggest"]
    assert all(item.review is None for item in out)
    assert meta["verification_ms"] == 0
    assert meta["verifier_model"] is None


def test_single_rule_cache_avoids_both_model_calls(monkeypatch):
    hit = {
        "suggestions": [
            {
                "rule_id": "budget-floor",
                "label": "State the budget",
                "text": "Budget is 12000 EUR.",
            }
        ],
        "meta": {"screened": True, "iterations": 1, "verifier_model": "deepseek/deepseek-v4-flash"},
    }

    async def cache_hit(key):
        return hit

    async def must_not_call(*args, **kwargs):
        raise AssertionError("cached suggestions must not call the provider")

    monkeypatch.setattr(scorer.cache, "get_json", cache_hit)
    monkeypatch.setattr(scorer.llm_client, "complete", must_not_call)
    out, meta = asyncio.run(scorer.suggest(BRIEF, "budget-floor", "en-GB", None, None))
    assert out[0].text == "Budget is 12000 EUR."
    assert meta["cached"] is True
    assert meta["generation_ms"] == 0
    assert meta["verification_ms"] == 0
