"""Orchestration: turn a brief into a scored, gated verdict.

Mock judging runs in a threadpool (it's pure CPU). LLM judging is a single
batched call for all rules, cached by (ruleset_version, brief) — safe because
the judge runs at temperature 0.
"""

from __future__ import annotations

import asyncio
import hashlib

from perfect_brief import aggregate, judge_all, llm, load_bundled, loader
from perfect_brief.judge import MockJudge
from perfect_brief.score import Finding, Status, Verdict

from . import cache, llm_client
from .models import (
    GateOut,
    ScoreResponse,
    Suggestion,
    VerdictOut,
)
from .settings import LOCALE_NAMES, settings

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


async def _judge(brief: str, judge_kind: str, model: str | None) -> tuple[list[Verdict], bool, str | None]:
    """Return (verdicts, cached, resolved_model)."""
    if judge_kind == "mock":
        verdicts = await asyncio.to_thread(judge_all, MockJudge(), _RULES, brief, "brief")
        return verdicts, False, None

    use = llm_client.resolve_model(model)
    # a verdict is reproducible only against (ruleset_version, model)
    key = f"pb:v:{_VERSION}:llm:{use}:{_sha(brief)}"
    hit = await cache.get_json(key)
    if hit:
        return _verdicts_from_cache(hit), True, use

    prompt = llm.render_judge_prompt(_RULES, brief, _CFG.budget_floor)
    raw = await llm_client.complete(prompt, use)
    verdicts = llm.parse_judge(_RULES, raw)
    await cache.set_json(key, _verdicts_to_cache(verdicts), settings().cache_ttl_seconds)
    return verdicts, False, use


async def score(brief: str, locale: str, judge_kind: str, model: str | None = None) -> ScoreResponse:
    verdicts, cached, used_model = await _judge(brief, judge_kind, model)
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


async def suggest(brief: str, rule_id: str, locale: str, model: str | None = None) -> list[Suggestion]:
    rule = _RULES.get(rule_id)
    if rule is None:
        raise KeyError(rule_id)
    prompt = llm.render_suggest_prompt(rule, brief, LOCALE_NAMES.get(locale))
    raw = await llm_client.complete(prompt, model)
    return [Suggestion(rule_id=rule_id, label=s["label"], text=s["text"]) for s in llm.parse_suggestions(raw)]


async def suggest_all(
    brief: str, rule_ids: list[str] | None, locale: str, model: str | None = None
) -> list[Suggestion]:
    if rule_ids is None:
        verdicts = await asyncio.to_thread(judge_all, MockJudge(), _RULES, brief, "brief")
        rule_ids = [
            v.rule_id
            for v in verdicts
            if v.status in (Status.PARTIAL, Status.FAIL) and v.rule_id != "anonymised"
        ]
    subset = [_RULES[i] for i in rule_ids if i in _RULES]
    if not subset:
        return []
    prompt = llm.render_suggest_all_prompt(subset, brief, LOCALE_NAMES.get(locale))
    raw = await llm_client.complete(prompt, model)
    by = llm.parse_suggestions_all(raw)
    return [Suggestion(rule_id=r.id, label=r.title, text=by[r.id]) for r in subset if r.id in by]
