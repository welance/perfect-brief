"""Orchestration: turn a brief into a scored, gated verdict.

Mock judging runs in a threadpool (it's pure CPU). LLM judging is a single
batched call for all rules, cached by (ruleset_version, brief) — safe because
the judge runs at temperature 0.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

from perfect_brief import aggregate, judge_all, llm, load_bundled, loader
from perfect_brief.judge import MockJudge
from perfect_brief.llm import FIXHINT
from perfect_brief.score import Finding, Status, Verdict

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


def _verdicts_from_cache(data: list[dict]) -> list[Verdict]:
    return [
        Verdict(
            d["rule_id"],
            Status(d["status"]),
            float(d["confidence"]),
            (Finding(d.get("quote", ""), d.get("note", "")),),
        )
        for d in data
    ]


async def _judge(
    brief: str, judge_kind: str, model: str | None, api_key: str | None
) -> tuple[list[Verdict], bool, str | None]:
    """Return (verdicts, cached, resolved_model)."""
    if judge_kind == "mock":
        verdicts = await asyncio.to_thread(judge_all, MockJudge(), _RULES, brief, "brief")
        return verdicts, False, None

    use = llm_client.resolve_model(model, allow_any=bool(api_key))
    # a verdict is reproducible only against (ruleset_version, model)
    key = f"pb:v:{_VERSION}:llm:{use}:{_sha(brief)}"
    hit = await cache.get_json(key)
    if hit:
        return _verdicts_from_cache(hit), True, use

    prompt = llm.render_judge_prompt(_RULES, brief, _CFG.budget_floor)
    raw = await llm_client.complete(prompt, use, api_key)
    verdicts = llm.parse_judge(_RULES, raw)
    await cache.set_json(key, _verdicts_to_cache(verdicts), settings().cache_ttl_seconds)
    return verdicts, False, use


async def score(
    brief: str, locale: str, judge_kind: str, model: str | None = None, api_key: str | None = None
) -> ScoreResponse:
    verdicts, cached, used_model = await _judge(brief, judge_kind, model, api_key)
    breakdown = aggregate(verdicts, _RULES, _CFG)
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
        gate=GateOut(passed=breakdown.gate_passed, missing=breakdown.gate_missing),
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
) -> dict[str, dict] | None:
    """items: [{"id","requirement","text"}] → id → {"accepted","reason"}; None = verifier down."""
    if not items:
        return {}
    try:
        raw = await llm_client.complete(llm.render_review_prompt(items, brief), verifier_model, api_key)
        return llm.parse_review(raw)
    except Exception as exc:  # noqa: BLE001 — degradation, never failure
        log.warning("suggestion review failed (%s); returning unscreened", exc)
        return None


async def suggest(
    brief: str, rule_id: str, locale: str, model: str | None = None, api_key: str | None = None
) -> tuple[list[Suggestion], dict]:
    """Single-rule options. One review pass, no retries: the human picks among
    the options, and a rejected one shown with its objection is informative."""
    rule = _RULES.get(rule_id)
    if rule is None:
        raise KeyError(rule_id)
    judge_model = llm_client.resolve_model(model, allow_any=bool(api_key))
    verifier = llm_client.resolve_verifier_model(judge_model)

    prompt = llm.render_suggest_prompt(rule, brief, LOCALE_NAMES.get(locale))
    raw = await llm_client.complete(prompt, model, api_key)
    opts = [s for s in llm.parse_suggestions(raw) if _sane(s["text"])]

    items = [
        {"id": str(i), "requirement": _requirement(rule), "text": s["text"]} for i, s in enumerate(opts)
    ]
    review = await _review_items(items, brief, verifier, api_key)

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
    return out, {"screened": screened, "iterations": 1, "verifier_model": verifier if review is not None else None}


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
        return [], {"screened": True, "iterations": 0, "verifier_model": None}

    judge_model = llm_client.resolve_model(model, allow_any=bool(api_key))
    verifier = llm_client.resolve_verifier_model(judge_model)
    locale_name = LOCALE_NAMES.get(locale)

    cache_key = "pb:s:" + ":".join(
        [_VERSION, judge_model, verifier, _sha(brief), ",".join(sorted(r.id for r in subset)), locale]
    )
    if not api_key:  # BYOK responses are never cached (caller-specific spend)
        hit = await cache.get_json(cache_key)
        if hit is not None:
            return [Suggestion(**s) for s in hit["suggestions"]], hit["meta"]

    done: dict[str, Suggestion] = {}
    critiques: dict[str, str] = {}
    pending = list(subset)
    iterations = 0
    verifier_up = True

    while pending and iterations < 1 + MAX_REVIEW_RETRIES:
        iterations += 1
        last_round = iterations >= 1 + MAX_REVIEW_RETRIES
        prompt = llm.render_suggest_all_prompt(pending, brief, locale_name, critiques or None)
        by = llm.parse_suggestions_all(await llm_client.complete(prompt, model, api_key))
        batch = [r for r in pending if r.id in by and _sane(by[r.id])]
        if not batch:
            break

        items = [{"id": r.id, "requirement": _requirement(r), "text": by[r.id]} for r in batch]
        review = await _review_items(items, brief, verifier, api_key)
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
    }
    if not api_key:
        await cache.set_json(
            cache_key,
            {"suggestions": [s.model_dump() for s in out], "meta": meta},
            settings().cache_ttl_seconds,
        )
    return out, meta
