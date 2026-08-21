"""Orchestration: turn a brief into a scored, gated verdict.

Mock judging runs in a threadpool (it's pure CPU). LLM judging is a single
batched call for all rules, cached by (ruleset_version, brief) — safe because
the judge runs at temperature 0.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time

from perfect_brief import aggregate, judge_all, llm, load_bundled, loader
from perfect_brief.judge import MockJudge
from perfect_brief.llm import FIXHINT
from perfect_brief.score import Status, Verdict

from . import cache, llm_client
from .models import (
    GateOut,
    ReviewOut,
    ScoreResponse,
    Suggestion,
    VerdictOut,
)
from .settings import LOCALE_NAMES, settings

log = logging.getLogger("perfect_brief.scorer")

_RULES, _CFG = load_bundled()
_VERSION = loader.ruleset_version()
_ENGINE = f"perfect-brief@{_VERSION}"


def rules():
    return _RULES


def cfg():
    return _CFG


def version() -> str:
    return _VERSION


def engine() -> str:
    return _ENGINE


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _verdicts_to_cache(verdicts: list[Verdict]) -> list[dict]:
    return [
        {
            "rule_id": v.rule_id,
            "status": v.status.value,
            "confidence": v.confidence,
            "quote": v.findings[0].quote if v.findings else "",
            "note": v.findings[0].note if v.findings else "",
        }
        for v in verdicts
    ]


def _verdicts_from_cache(data: list[dict], brief: str) -> list[Verdict]:
    # Cache content crosses a trust boundary too: Redis may hold an old shape,
    # a partial write, or data written by a misconfigured peer. Reuse the exact
    # strict parser used for provider output, including verbatim evidence.
    return llm.parse_judge(_RULES, json.dumps(data), brief)


async def _judge(
    brief: str, judge_kind: str, model: str | None, api_key: str | None, no_cache: bool = False
) -> tuple[list[Verdict], bool, str | None]:
    """Return (verdicts, cached, resolved_model)."""
    if judge_kind == "mock":
        verdicts = await asyncio.to_thread(judge_all, MockJudge(), _RULES, brief, "brief")
        return verdicts, False, None

    use = llm_client.resolve_model(model, allow_any=bool(api_key))
    # a verdict is reproducible only against (ruleset_version, model)
    strategy = f"batch-{settings().judge_batch_size or 'all'}"
    key = f"pb:v:{_VERSION}:llm:{_sha(use)}:{strategy}:{_sha(brief)}"
    # A caller supplying their own key reasonably expects a fresh call billed
    # to that key, not an answer produced earlier on somebody else's account.
    cache_allowed = not no_cache and not api_key
    if cache_allowed:
        hit = await cache.get_json(key)
        if hit:
            try:
                return _verdicts_from_cache(hit, brief), True, use
            except (KeyError, TypeError, ValueError) as exc:
                log.warning("discarding invalid verdict cache entry: %s", exc)

    batch_size = settings().judge_batch_size
    if batch_size <= 0 or batch_size >= len(_RULES):
        prompt = llm.render_judge_prompt(_RULES, brief, _CFG.budget_floor)
        raw = await llm_client.complete(prompt, use, api_key)
        verdicts = llm.parse_judge(_RULES, raw, brief)
    else:
        items = list(_RULES.items())
        batches = [dict(items[i : i + batch_size]) for i in range(0, len(items), batch_size)]
        semaphore = asyncio.Semaphore(max(1, settings().judge_concurrency))

        async def judge_batch(batch: dict) -> list[Verdict]:
            async with semaphore:
                prompt = llm.render_judge_prompt(batch, brief, _CFG.budget_floor)
                raw = await llm_client.complete(prompt, use, api_key)
                return llm.parse_judge(batch, raw, brief)

        # If one batch fails, cancel its siblings instead of continuing to
        # spend tokens on a score that can no longer be returned. Keep the
        # original exception type so the API can distinguish truncation from
        # an upstream failure (TaskGroup would wrap it in ExceptionGroup).
        tasks = [asyncio.create_task(judge_batch(batch)) for batch in batches]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        failure = next((task.exception() for task in done if task.exception() is not None), None)
        if failure is not None:
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            raise failure
        await asyncio.gather(*pending)
        verdicts = [verdict for task in tasks for verdict in task.result()]
        if {v.rule_id for v in verdicts} != set(_RULES) or len(verdicts) != len(_RULES):
            raise llm.JudgeUnparsable("the merged judge batches are incomplete")
    if cache_allowed:
        await cache.set_json(key, _verdicts_to_cache(verdicts), settings().cache_ttl_seconds)
    return verdicts, False, use


async def score(
    brief: str,
    locale: str,
    judge_kind: str,
    model: str | None = None,
    api_key: str | None = None,
    gate_contexts: list[str] | None = None,
    no_cache: bool = False,
) -> ScoreResponse:
    verdicts, cached, used_model = await _judge(brief, judge_kind, model, api_key, no_cache)
    breakdown = aggregate(verdicts, _RULES, _CFG, contexts=gate_contexts)
    vmap = {v.rule_id: v for v in verdicts}
    out_verdicts = [
        VerdictOut(
            rule_id=r.id,
            status=vmap[r.id].status.value if r.id in vmap else "not_applicable",
            confidence=vmap[r.id].confidence if r.id in vmap else 0.0,
            quote=(vmap[r.id].findings[0].quote if r.id in vmap and vmap[r.id].findings else ""),
            note=(vmap[r.id].findings[0].note if r.id in vmap and vmap[r.id].findings else ""),
            weight=r.weight,
            severity=r.severity,
            gate=r.gate,
        )
        for r in _RULES.values()
    ]
    return ScoreResponse(
        score=breakdown.score,
        band=breakdown.band,
        decision=breakdown.decision,
        decision_label=breakdown.decision_label,
        gate=GateOut(
            passed=breakdown.gate_passed,
            missing=breakdown.gate_missing,
            contexts=breakdown.gate_contexts,
        ),
        verdicts=out_verdicts,
        review_required=breakdown.review_required,
        low_confidence=breakdown.low_confidence,
        ruleset_version=_VERSION,
        engine=_ENGINE,
        judge=judge_kind,  # type: ignore[arg-type]
        model=used_model,
        cached=cached,
    )


# ---- suggestion verifier loop ---------------------------------------------
# The LLM only returns accept/reject verdicts; this code owns the retry
# policy, the sanity screen, and the final decision. Verifier failure never
# fails a request — suggestions ship unscreened (review=None).

MAX_REVIEW_RETRIES = 2
_MAX_SUGGESTION_CHARS = 600


def _sane(text: str) -> bool:
    return bool(text and text.strip()) and len(text) <= _MAX_SUGGESTION_CHARS


def _requirement(rule) -> str:
    return FIXHINT.get(rule.id, rule.criteria.strip())


async def _review_items(
    items: list[dict], brief: str, verifier_model: str, api_key: str | None
) -> tuple[dict[str, dict] | None, int]:
    """items: [{"id","requirement","text"}] → id → {"accepted","reason"}; None = verifier down."""
    if not items:
        return {}, 0
    started = time.monotonic()
    try:
        raw = await llm_client.complete(
            llm.render_review_prompt(items, brief),
            verifier_model,
            api_key,
            max_tokens=settings().verifier_max_tokens,
            purpose="verify",
        )
        return llm.parse_review(raw), round((time.monotonic() - started) * 1000)
    except Exception as exc:  # noqa: BLE001 — degradation, never failure
        log.warning("suggestion review failed (%s); returning unscreened", exc)
        return None, round((time.monotonic() - started) * 1000)


def _suggestions_from_cache(hit: object) -> tuple[list[Suggestion], dict] | None:
    """Validate ephemeral Redis data before returning it across the API boundary."""
    try:
        if not isinstance(hit, dict) or not isinstance(hit["suggestions"], list):
            raise TypeError("unexpected suggestion cache shape")
        raw_meta = hit["meta"]
        if not isinstance(raw_meta, dict):
            raise TypeError("unexpected suggestion cache metadata")
        out = [Suggestion(**item) for item in hit["suggestions"]]
        meta = {
            "screened": bool(raw_meta["screened"]),
            "iterations": int(raw_meta["iterations"]),
            "verifier_model": raw_meta.get("verifier_model"),
            "model": raw_meta.get("model"),
            "cached": True,
            "generation_ms": 0,
            "verification_ms": 0,
        }
        return out, meta
    except (KeyError, TypeError, ValueError) as exc:
        log.warning("discarding invalid suggestion cache entry: %s", exc)
        return None


async def suggest(
    brief: str, rule_id: str, locale: str, model: str | None = None, api_key: str | None = None
) -> tuple[list[Suggestion], dict]:
    """Single-rule options. One review pass, no retries: the human picks among
    the options, and a rejected one shown with its objection is informative."""
    rule = _RULES.get(rule_id)
    if rule is None:
        raise KeyError(rule_id)
    suggest_model = llm_client.resolve_suggest_model(model, allow_any=bool(api_key))
    verifier = llm_client.resolve_verifier_model(suggest_model)

    cache_key = "pb:s2:one:" + ":".join([_VERSION, suggest_model, verifier, _sha(brief), rule_id, locale])
    if not api_key:
        cached = _suggestions_from_cache(await cache.get_json(cache_key))
        if cached is not None:
            return cached

    prompt = llm.render_suggest_prompt(rule, brief, LOCALE_NAMES.get(locale))
    started = time.monotonic()
    raw = await llm_client.complete(
        prompt,
        suggest_model,
        api_key,
        max_tokens=settings().suggest_max_tokens,
        purpose="suggest",
    )
    generation_ms = round((time.monotonic() - started) * 1000)
    opts = [s for s in llm.parse_suggestions(raw) if _sane(s["text"])]

    items = [{"id": str(i), "requirement": _requirement(rule), "text": s["text"]} for i, s in enumerate(opts)]
    review, verification_ms = await _review_items(items, brief, verifier, api_key)

    out: list[Suggestion] = []
    for i, s in enumerate(opts):
        verdict = None if review is None else review.get(str(i))
        out.append(
            Suggestion(
                rule_id=rule_id,
                label=s["label"],
                text=s["text"],
                review=None if verdict is None else ReviewOut(**verdict),
                verifier_model=None if verdict is None else verifier,
            )
        )
    screened = review is not None and all(s.review and s.review.accepted for s in out)
    meta = {
        "screened": screened,
        "iterations": 1,
        "verifier_model": verifier if review is not None else None,
        "model": suggest_model,
        "cached": False,
        "generation_ms": generation_ms,
        "verification_ms": verification_ms,
    }
    if not api_key and review is not None:
        await cache.set_json(
            cache_key,
            {"suggestions": [s.model_dump() for s in out], "meta": meta},
            settings().cache_ttl_seconds,
        )
    return out, meta


async def suggest_all(
    brief: str,
    rule_ids: list[str] | None,
    locale: str,
    model: str | None = None,
    api_key: str | None = None,
) -> tuple[list[Suggestion], dict]:
    """One suggestion per failing rule, screened by the verifier model.
    Rejected suggestions are regenerated with the reviewer's critique fed
    back, up to MAX_REVIEW_RETRIES; the last attempt ships with its rejected
    review attached (best effort, flagged via meta/screened)."""
    if rule_ids is None:
        verdicts = await asyncio.to_thread(judge_all, MockJudge(), _RULES, brief, "brief")
        rule_ids = [
            v.rule_id
            for v in verdicts
            if v.status in (Status.PARTIAL, Status.FAIL) and v.rule_id != "anonymised"
        ]
    subset = [_RULES[i] for i in rule_ids if i in _RULES]
    if not subset:
        return [], {
            "screened": True,
            "iterations": 0,
            "verifier_model": None,
            "model": None,
            "cached": False,
            "generation_ms": 0,
            "verification_ms": 0,
        }

    suggest_model = llm_client.resolve_suggest_model(model, allow_any=bool(api_key))
    verifier = llm_client.resolve_verifier_model(suggest_model)
    locale_name = LOCALE_NAMES.get(locale)

    cache_key = "pb:s2:all:" + ":".join(
        [_VERSION, suggest_model, verifier, _sha(brief), ",".join(sorted(r.id for r in subset)), locale]
    )
    if not api_key:  # BYOK responses are never cached (caller-specific spend)
        cached = _suggestions_from_cache(await cache.get_json(cache_key))
        if cached is not None:
            return cached

    done: dict[str, Suggestion] = {}
    critiques: dict[str, str] = {}
    pending = list(subset)
    iterations = 0
    verifier_up = True
    generation_ms = 0
    verification_ms = 0

    while pending and iterations < 1 + MAX_REVIEW_RETRIES:
        iterations += 1
        last_round = iterations >= 1 + MAX_REVIEW_RETRIES
        prompt = llm.render_suggest_all_prompt(pending, brief, locale_name, critiques or None)
        started = time.monotonic()
        raw = await llm_client.complete(
            prompt,
            suggest_model,
            api_key,
            max_tokens=settings().suggest_all_max_tokens,
            purpose="suggest-all",
        )
        generation_ms += round((time.monotonic() - started) * 1000)
        by = llm.parse_suggestions_all(raw)
        batch = [r for r in pending if r.id in by and _sane(by[r.id])]
        if not batch:
            break

        items = [{"id": r.id, "requirement": _requirement(r), "text": by[r.id]} for r in batch]
        review, review_ms = await _review_items(items, brief, verifier, api_key)
        verification_ms += review_ms
        if review is None:  # verifier down: ship this round unscreened
            verifier_up = False
            for r in batch:
                done[r.id] = Suggestion(rule_id=r.id, label=r.title, text=by[r.id])
            pending = []
            break

        still = []
        for r in batch:
            verdict = review.get(r.id, {"accepted": False, "reason": "no verdict returned"})
            if verdict["accepted"] or last_round:
                done[r.id] = Suggestion(
                    rule_id=r.id,
                    label=r.title,
                    text=by[r.id],
                    review=ReviewOut(**verdict),
                    verifier_model=verifier,
                )
            else:
                critiques[r.id] = verdict["reason"]
                still.append(r)
        pending = still

    out = [done[r.id] for r in subset if r.id in done]
    screened = verifier_up and bool(out) and all(s.review and s.review.accepted for s in out)
    meta = {
        "screened": screened,
        "iterations": iterations,
        "verifier_model": verifier if verifier_up else None,
        "model": suggest_model,
        "cached": False,
        "generation_ms": generation_ms,
        "verification_ms": verification_ms,
    }
    if not api_key and screened:
        await cache.set_json(
            cache_key,
            {"suggestions": [s.model_dump() for s in out], "meta": meta},
            settings().cache_ttl_seconds,
        )
    return out, meta
