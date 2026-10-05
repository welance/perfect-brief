"""Hostile and partial model output must never influence a score."""

import asyncio
import json

import pytest

from app import scorer
from app.settings import settings
from brief_bar import load_bundled
from brief_bar.llm import JudgeUnparsable, is_evidence, parse_judge

RULES, _ = load_bundled()
BRIEF = "# Portal\nProblem: bookings arrive by phone."


def verdicts_for(rules=RULES):
    return [
        {"rule_id": rid, "status": "fail", "confidence": 0.9, "quote": "", "note": "missing"} for rid in rules
    ]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda values: values[:-1],
        lambda values: values + [values[0]],
        lambda values: [{**values[0], "rule_id": "not-a-rule"}] + values[1:],
        lambda values: [{**values[0], "status": "maybe"}] + values[1:],
        lambda values: [{**values[0], "confidence": 2}] + values[1:],
    ],
)
def test_incomplete_or_hostile_verdict_sets_are_refused(mutate):
    with pytest.raises(JudgeUnparsable):
        parse_judge(RULES, json.dumps(mutate(verdicts_for())), BRIEF)


def test_non_array_and_invented_quote_are_refused():
    with pytest.raises(JudgeUnparsable):
        parse_judge(RULES, json.dumps({"verdicts": verdicts_for()}), BRIEF)
    values = verdicts_for()
    values[0]["quote"] = "words that do not occur"
    with pytest.raises(JudgeUnparsable):
        parse_judge(RULES, json.dumps(values), BRIEF)


EVIDENCE_SOURCE = (
    "# Fleet planning\n\n## What we get\n\nWhat we get at the end: the driver app must let a user "
    "mark a stop \u2018Delivered\u2019 \u2014 it won\u2019t need signal.\n\n- Two dispatchers plan the day\n"
    "- **Eighteen drivers** use a phone"
)


@pytest.mark.parametrize(
    "quote",
    [
        "The driver app must let a user mark a stop",  # the judge capitalised a sentence start
        "mark a stop 'Delivered' - it won't need signal",  # straight quotes, a plain dash
        "the driver app must let a user\nmark a stop",  # a line break where the brief has a space
        "Eighteen drivers use a phone",  # markdown emphasis left out
        "the driver app must let a user ... it won\u2019t need signal.",  # words left out of the middle
        "Two dispatchers plan the day\u2026 Eighteen drivers use a phone",
    ],
)
def test_a_faithful_quote_is_evidence_whatever_its_typography(quote):
    assert is_evidence(quote, EVIDENCE_SOURCE)


@pytest.mark.parametrize(
    "quote",
    [
        "the driver app must let a customer mark a stop",  # one word that is not in the brief
        "Eighteen drivers use a phone ... Two dispatchers plan the day",  # real words, wrong order
        "nineteen drivers",
        "...",
        "\u2026",
    ],
)
def test_invented_or_reordered_words_are_never_evidence(quote):
    assert not is_evidence(quote, EVIDENCE_SOURCE)


def test_an_unusable_answer_is_asked_for_again_once(monkeypatch):
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PB_JUDGE_BATCH_SIZE", "0")
    settings.cache_clear()
    answers = iter(
        [
            json.dumps([{**v, "quote": "words that do not occur"} for v in verdicts_for()]),
            json.dumps(verdicts_for()),
        ]
    )
    calls = 0

    async def fake_complete(prompt, model=None, api_key=None):
        nonlocal calls
        calls += 1
        return next(answers)

    monkeypatch.setattr(scorer.llm_client, "complete", fake_complete)
    monkeypatch.setattr(scorer.cache, "get_json", lambda key: _none())
    monkeypatch.setattr(scorer.cache, "set_json", lambda *a, **k: _none())
    asyncio.run(scorer.score(BRIEF, "en-GB", "llm"))
    assert calls == 2
    settings.cache_clear()


def test_an_answer_that_stays_unusable_is_still_refused(monkeypatch):
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PB_JUDGE_BATCH_SIZE", "0")
    settings.cache_clear()
    calls = 0

    async def fake_complete(prompt, model=None, api_key=None):
        nonlocal calls
        calls += 1
        return json.dumps([{**v, "quote": "words that do not occur"} for v in verdicts_for()])

    monkeypatch.setattr(scorer.llm_client, "complete", fake_complete)
    monkeypatch.setattr(scorer.cache, "get_json", lambda key: _none())
    with pytest.raises(JudgeUnparsable):
        asyncio.run(scorer.score(BRIEF, "en-GB", "llm"))
    assert calls == 2
    settings.cache_clear()


def test_the_retry_budget_is_per_request_not_per_batch(monkeypatch):
    """A brief that makes every batch misquote costs one extra call, not one per batch."""
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PB_JUDGE_BATCH_SIZE", "5")
    monkeypatch.setenv("PB_JUDGE_CONCURRENCY", "1")
    settings.cache_clear()
    calls = 0

    async def fake_complete(prompt, model=None, api_key=None):
        nonlocal calls
        calls += 1
        ids = [rid for rid in RULES if f"- {rid}:" in prompt]
        return json.dumps(
            [
                {
                    "rule_id": rid,
                    "status": "fail",
                    "confidence": 0.9,
                    "quote": "words that do not occur",
                    "note": "x",
                }
                for rid in ids
            ]
        )

    monkeypatch.setattr(scorer.llm_client, "complete", fake_complete)
    monkeypatch.setattr(scorer.cache, "get_json", lambda key: _none())
    with pytest.raises(JudgeUnparsable):
        asyncio.run(scorer.score(BRIEF, "en-GB", "llm"))
    # Three batches. One retry for the whole request: at most one call per
    # batch plus that single retry — never a retry per batch (which is six).
    assert 2 <= calls <= 4
    settings.cache_clear()


def test_concurrent_batches_are_complete_and_keep_rule_order(monkeypatch):
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PB_JUDGE_BATCH_SIZE", "5")
    monkeypatch.setenv("PB_JUDGE_CONCURRENCY", "2")
    settings.cache_clear()


def test_failed_batch_cancels_siblings_and_preserves_error_type(monkeypatch):
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PB_JUDGE_BATCH_SIZE", "5")
    monkeypatch.setenv("PB_JUDGE_CONCURRENCY", "3")
    settings.cache_clear()
    cancelled = 0

    async def fake_complete(prompt, model=None, api_key=None):
        nonlocal cancelled
        if "- timeline:" in prompt:
            return "not-json"
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled += 1
            raise
        return "[]"

    monkeypatch.setattr(scorer.llm_client, "complete", fake_complete)
    monkeypatch.setattr(scorer.cache, "get_json", lambda key: _none())
    with pytest.raises(JudgeUnparsable):
        asyncio.run(scorer.score(BRIEF, "en-GB", "llm"))
    assert cancelled >= 1
    settings.cache_clear()
    calls: list[list[str]] = []

    async def fake_complete(prompt, model=None, api_key=None):
        ids = [rid for rid in RULES if f"- {rid}:" in prompt]
        calls.append(ids)
        await asyncio.sleep(0)
        return json.dumps(verdicts_for({rid: RULES[rid] for rid in ids}))

    monkeypatch.setattr(scorer.llm_client, "complete", fake_complete)
    monkeypatch.setattr(scorer.cache, "get_json", lambda key: _none())
    monkeypatch.setattr(scorer.cache, "set_json", lambda key, value, ttl: _none())
    result = asyncio.run(scorer.score(BRIEF, "en-GB", "llm"))
    assert [v.rule_id for v in result.verdicts] == list(RULES)
    assert [len(call) for call in calls] == [5, 5, 4]
    settings.cache_clear()


async def _none():
    return None


def test_byok_and_model_header_abuse_is_bounded(client):
    too_long = "x" * (settings().byok_max_chars + 1)
    r = client.post("/v1/score", json={"brief": BRIEF, "judge": "llm"}, headers={"x-llm-key": too_long})
    assert r.status_code == 400

    r = client.post(
        "/v1/score",
        json={"brief": BRIEF, "judge": "llm", "model": "vendor/model\nforged-log"},
        headers={"x-llm-key": "key"},
    )
    assert r.status_code in {422, 503}


def test_public_responses_carry_baseline_browser_security_headers(client):
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "camera=()" in response.headers["permissions-policy"]


def test_corrupt_cache_is_ignored_not_scored(monkeypatch):
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PB_JUDGE_BATCH_SIZE", "0")
    settings.cache_clear()

    async def corrupt(_key):
        return [{"rule_id": "clear-title", "status": "pass", "confidence": 0.9}]

    async def complete(prompt, model=None, api_key=None):
        return json.dumps(verdicts_for())

    monkeypatch.setattr(scorer.cache, "get_json", corrupt)
    monkeypatch.setattr(scorer.cache, "set_json", lambda key, value, ttl: _none())
    monkeypatch.setattr(scorer.llm_client, "complete", complete)
    result = asyncio.run(scorer.score(BRIEF, "en-GB", "llm"))
    assert result.cached is False
    assert len(result.verdicts) == len(RULES)
    settings.cache_clear()


def test_server_paid_llm_has_a_separate_ip_budget(client, monkeypatch):
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "server-key")
    settings.cache_clear()
    calls: list[tuple[str, int | None]] = []

    async def allow(bucket, limit=None):
        calls.append((bucket, limit))
        return limit != settings().paid_llm_rate_limit_per_minute

    monkeypatch.setattr(scorer.cache, "allow", allow)
    # main and scorer share the same imported cache module
    response = client.post(
        "/v1/score",
        json={"brief": BRIEF, "judge": "llm"},
        headers={"x-api-key": "rotating-untrusted-label"},
    )
    assert response.status_code == 429
    assert calls[-1][1] == settings().paid_llm_rate_limit_per_minute
    assert calls[-1][0].startswith("paid:")
    settings.cache_clear()


def test_byok_does_not_consume_the_service_paid_budget(client, monkeypatch):
    calls: list[int | None] = []

    async def allow(bucket, limit=None):
        calls.append(limit)
        return False

    monkeypatch.setattr(scorer.cache, "allow", allow)
    response = client.post(
        "/v1/score",
        json={"brief": BRIEF, "judge": "llm"},
        headers={"x-llm-key": "caller-funded-key"},
    )
    # The general request limiter rejects it; importantly no second paid-limit
    # check happened before that and the caller's key never changes the budget.
    assert response.status_code == 429
    assert calls == [None]
