"""The free, bring-your-own-model contract: `/v1/byo/*`.

Everything a client's own model needs to judge a brief against the live bar,
and one call that turns its verdicts into the bar's number with the engine the
service itself scores with. No route here calls a provider, accepts a provider
key, or falls back to the service judge: this module does not import the LLM
client at all, and a test holds it to that.

The hosted MCP connector at /mcp and the stdio adapter in mcp-server/ are thin
doors onto these same functions.

Authority stays where it was. `/v1/score` is the authoritative score the
welance/directory publishes on; a client-judged result here is tagged
`evaluation_source: "client"`, `authoritative: false`, and carries nothing a
consumer could present as permission to publish.
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from brief_bar import aggregate, byo

from . import scorer
from .settings import settings
from .version import SERVICE_VERSION

DIRECTORY_LABEL = "Find a team on welance/directory →"
MAX_VERDICTS = 200


def directory_link() -> dict[str, str]:
    return {"label": DIRECTORY_LABEL, "url": settings().directory_url}


def guard(brief: str) -> None:
    if not brief.strip():
        raise HTTPException(status_code=422, detail="brief is empty")
    if len(brief) > settings().request_max_chars:
        raise HTTPException(status_code=413, detail=f"brief exceeds {settings().request_max_chars} chars")


# ---- the service layer: one function per tool, shared by REST and MCP --------


def rules_payload() -> dict[str, Any]:
    return byo.rubric(scorer.rules(), scorer.cfg(), scorer.version())


def template_payload() -> dict[str, Any]:
    return byo.brief_template(scorer.rules(), scorer.cfg(), scorer.version())


def judge_prompt_payload(brief: str | None = None) -> dict[str, Any]:
    if brief is not None and brief.strip():
        guard(brief)
    rules = scorer.rules()
    return {
        "contract": byo.CONTRACT,
        "ruleset_version": scorer.version(),
        "prompt": byo.judge_prompt(rules, scorer.cfg(), brief),
        "placeholder": None if brief and brief.strip() else byo.BRIEF_PLACEHOLDER,
        "verdict_schema": byo.verdict_schema(rules),
        "rule_ids": list(rules),
        "instructions": [
            "Run this prompt on your own model, at temperature 0 if you can.",
            "Return only the JSON array the prompt asks for: one verdict per rule, each rule once.",
            "Send that array, the same brief and this ruleset_version to aggregate_verdicts.",
            "Every rule is judged, even with directory_context off: aggregation drops the policy rules.",
        ],
        "evaluation_source": byo.EVALUATION_SOURCE,
        "provider_calls": 0,
    }


def improvement_prompt_payload(
    brief: str, verdicts: list[dict] | None = None, directory_context: bool = True
) -> dict[str, Any]:
    guard(brief)
    active = byo.active_contexts(directory_context)
    parsed = None
    errors: list[dict] = []
    if verdicts:
        parsed, errors, evidence, _ = byo.validate_verdicts(scorer.rules(), verdicts, brief)
        errors = errors + evidence
    return {
        "contract": byo.CONTRACT,
        "ruleset_version": scorer.version(),
        "prompt": byo.improvement_prompt(scorer.rules(), scorer.cfg(), brief, parsed, active),
        "verdicts_used": parsed is not None,
        "verdict_errors": errors,
        "provider_calls": 0,
    }


def improvement_prompt_text(brief: str = "") -> str:
    """The prompt alone, for the MCP prompt surface; an empty brief leaves a paste-here line."""
    if brief.strip():
        guard(brief)
    return byo.improvement_prompt(scorer.rules(), scorer.cfg(), brief, None, None)


def check_payload(brief: str, directory_context: bool = True) -> dict[str, Any]:
    guard(brief)
    return byo.check_brief(brief, scorer.rules(), scorer.cfg(), scorer.version(), directory_context)


def aggregate_payload(
    brief: str, verdicts: Any, ruleset_version: str, directory_context: bool = True
) -> dict[str, Any]:
    """Validate a client's verdicts, then aggregate them with the service engine.

    The math is `brief_bar.aggregate`, the same call `/v1/score` makes, so the
    same verdicts give the same number. What differs is the trust: the
    verdicts are the client's, and the answer says so on every line.
    """
    guard(brief)
    rules, cfg, live = scorer.rules(), scorer.cfg(), scorer.version()
    active = byo.active_contexts(directory_context)
    errors: list[dict] = []
    if ruleset_version != live:
        errors.append(
            {
                "code": "ruleset_version_mismatch",
                "rule_id": None,
                "index": None,
                "message": f"verdicts were written for {ruleset_version!r}; the live bar is {live!r}. "
                "Fetch get_judge_prompt again and re-judge.",
            }
        )
    if isinstance(verdicts, list) and len(verdicts) > MAX_VERDICTS:
        verdicts = verdicts[:MAX_VERDICTS]
        errors.append(
            {"code": "too_many_verdicts", "rule_id": None, "index": None, "message": "too many verdicts"}
        )
    parsed, v_errors, evidence, warnings = byo.validate_verdicts(rules, verdicts, brief)
    errors += v_errors
    result = None
    conflicts: list[dict] = []
    if parsed is not None and not errors:
        b = aggregate(parsed, rules, cfg, contexts=active)
        vmap = {v.rule_id: v for v in parsed}
        conflicts = byo.conflicts(parsed, brief, active)
        result = {
            "score": b.score,
            "band": b.band,
            "decision": b.decision,
            "decision_label": f"{b.decision_label} (advisory: client-judged, not a publication decision)",
            "gate": {"passed": b.gate_passed, "missing": b.gate_missing, "contexts": b.gate_contexts},
            "verdicts": [
                {
                    "rule_id": r.id,
                    "status": vmap[r.id].status.value,
                    "confidence": vmap[r.id].confidence,
                    "quote": vmap[r.id].findings[0].quote if vmap[r.id].findings else "",
                    "note": vmap[r.id].findings[0].note if vmap[r.id].findings else "",
                    "weight": r.weight,
                    "severity": r.severity,
                    "gate": r.gate,
                    "excluded": r.id in b.excluded,
                }
                for r in rules.values()
            ],
            "review_required": b.review_required or bool(conflicts),
            "low_confidence": b.low_confidence,
        }
    return {
        "contract": byo.CONTRACT,
        "evaluation_source": byo.EVALUATION_SOURCE,
        "authoritative": False,
        "advisory": True,
        "publication_authority": "none",
        "notice": byo.ADVISORY_NOTICE,
        "ruleset_version": live,
        "engine": scorer.engine(),
        "brief_sha256": hashlib.sha256(brief.encode("utf-8")).hexdigest(),
        "valid": result is not None,
        "errors": errors,
        "evidence_errors": evidence,
        "warnings": warnings,
        "conflicts": conflicts,
        "result": result,
        "directory": directory_link(),
        "provider_calls": 0,
    }


def status_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "contract": byo.CONTRACT,
        "release_version": SERVICE_VERSION,
        "ruleset_version": scorer.version(),
        "rule_count": len(scorer.rules()),
        "mode": "bring-your-own-model",
        "provider_calls": 0,
        "llm_fallback": False,
        "evaluation_source": byo.EVALUATION_SOURCE,
        "capabilities": [
            "get_rules",
            "get_brief_template",
            "get_judge_prompt",
            "get_improvement_prompt",
            "check_brief",
            "aggregate_verdicts",
            "bar_status",
        ],
        "authoritative_scoring": "POST /v1/score (the service judge; what the welance/directory publishes on)",
        "directory": directory_link(),
    }


# ---- REST --------------------------------------------------------------------


class BriefIn(BaseModel):
    brief: str = Field(..., description="The brief text. Any language.")
    directory_context: bool = Field(
        True,
        description="Keep True for a brief headed to the welance/directory (anonymisation and the "
        "budget floor apply). False scores a generic brief without those policy rules.",
    )


class JudgePromptIn(BaseModel):
    brief: str | None = Field(
        None, description="Optional. Without it the prompt carries a {{BRIEF}} placeholder to fill in."
    )


class ImprovementIn(BriefIn):
    verdicts: list[dict[str, Any]] | None = Field(
        None, max_length=MAX_VERDICTS, description="Optional client verdicts, to target the gaps."
    )


class AggregateIn(BriefIn):
    ruleset_version: str = Field(
        ..., max_length=100, description="The ruleset_version the judge prompt was fetched at."
    )
    verdicts: list[Any] = Field(
        ..., max_length=MAX_VERDICTS, description="The client model's JSON array, one verdict per rule."
    )


def router(free_limit: Callable[[Request], Awaitable[None]]) -> APIRouter:
    """The /v1/byo routes, rate-limited like every other free call."""
    r = APIRouter(prefix="/v1/byo", tags=["byo"], dependencies=[Depends(free_limit)])

    @r.get("/rules", summary="The live bar, with the arithmetic, for your own model")
    async def get_rules() -> dict:
        """Every rule's id, title, criteria, weight, gate role and policy context, with how to
        pass it — plus the status scores, confidence threshold, bands, accept threshold and gate
        that turn verdicts into a number. The rule count is whatever the live catalogue holds.
        Free: no model runs."""
        return rules_payload()

    @r.get("/template", summary="A brief template built from the live rules")
    async def get_template() -> dict:
        """A Markdown brief with one section per rule, and the inputs each section needs (gate
        rules and policy contexts marked). Built from the live catalogue, so a new rule appears
        here without a release of this route. Free: no model runs."""
        return template_payload()

    @r.post("/judge-prompt", summary="The judge prompt and verdict schema, for your own model")
    async def post_judge_prompt(req: JudgePromptIn) -> dict:
        """The service judge's own prompt, word for word, with the brief embedded (or a
        `{{BRIEF}}` placeholder), and the JSON Schema your model's answer must meet. Run it on
        your own model, then send the answer to `/v1/byo/aggregate`. Free: no model runs here."""
        return judge_prompt_payload(req.brief)

    @r.post("/improvement-prompt", summary="A working order for improving a brief with your own model")
    async def post_improvement_prompt(req: ImprovementIn) -> dict:
        """A prompt for your own model that works through the gaps gate first, then by weight,
        in the author's voice and without invented scores or facts. Pass verdicts you already
        have to target the failing rules. Free: nothing is generated here."""
        return improvement_prompt_payload(req.brief, req.verdicts, req.directory_context)

    @r.post("/check", summary="Deterministic checks only — semantic coverage is incomplete")
    async def post_check(req: BriefIn) -> dict:
        """Pattern checks only: emails, URLs and phones, a stated budget and timeline,
        personal-data cues without a compliance cue, placeholders, title and sections. It does not
        judge meaning, so semantic coverage is incomplete and it never returns a score."""
        return check_payload(req.brief, req.directory_context)

    @r.post("/aggregate", summary="Aggregate your model's verdicts with the service engine (advisory)")
    async def post_aggregate(req: AggregateIn) -> dict:
        """Validates the verdicts against the live ruleset and the brief (every rule once, quotes
        verbatim, the version you judged at), then aggregates with the same engine as `/v1/score`.
        Any error means no score. The answer is client-judged and advisory
        (`evaluation_source: client`): it can never authorise publication on the welance/directory."""
        return aggregate_payload(req.brief, req.verdicts, req.ruleset_version, req.directory_context)

    @r.get("/status", summary="Capabilities of the free surface and the live ruleset")
    async def get_status() -> dict:
        """Which release and ruleset are live, the tools of the free surface, and the promise
        behind it: bring your own model, zero provider calls, no fallback to the service judge.
        Where authoritative scoring lives is named too."""
        return status_payload()

    return r
