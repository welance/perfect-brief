"""API request/response schemas.

Every field carries a one-line description and, where useful, an example —
the /docs page should explain itself without leaving the browser.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

JudgeKind = Literal["mock", "llm"]


class ScoreRequest(BaseModel):
    brief: str = Field(
        ...,
        description="The brief text to score. Any language.",
        examples=["# Booking tool\nProblem: staff can't update availability… Budget 25-40k."],
    )
    locale: str = Field(
        "en-GB",
        description="UI locale; fix suggestions come back in this language.",
        examples=["it"],
    )
    judge: JudgeKind | None = Field(
        None,
        description="'llm' = real judge · 'mock' = offline keyword stub (EN only). Default: server setting.",
    )
    model: str | None = Field(
        None,
        max_length=200,
        description="LLM for the judge; must appear in GET /v1/models. Part of the cache key.",
        examples=["claude-sonnet-4-6"],
    )
    gate_contexts: list[str] | None = Field(
        None,
        description="Policy contexts to enforce. null = all · [] = generic brief "
        "(drops the Directory-only rules: anonymised + €10k floor).",
        examples=[[]],
    )
    no_cache: bool = Field(
        default=False,
        description="Skip the verdict cache entirely: nothing about this brief is "
        "written down, not even the evidence quotes. Costs a fresh judge call.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "brief": "# Real-time availability for restaurant bookings\n"
                    "Problem: staff can't update availability across channels…\n"
                    "Budget band 25-40k. Ship before spring.",
                    "locale": "en-GB",
                    "judge": "llm",
                }
            ]
        }
    }


class SuggestRequest(BaseModel):
    brief: str = Field(..., description="The brief as it stands now.")
    rule_id: str = Field(..., description="The failing rule to fix.", examples=["success-metrics"])
    locale: str = Field("en-GB", description="Suggestions come back in this language.")
    model: str | None = Field(None, max_length=200, description="LLM override; must be in GET /v1/models.")


class SuggestAllRequest(BaseModel):
    brief: str = Field(..., description="The brief as it stands now.")
    rule_ids: list[str] | None = Field(
        None,
        description="Rules to fix. Default (null): every failing/partial rule.",
        examples=[["success-metrics", "timeline"]],
    )
    locale: str = Field("en-GB", description="Suggestions come back in this language.")
    model: str | None = Field(None, max_length=200, description="LLM override; must be in GET /v1/models.")


class VerdictOut(BaseModel):
    rule_id: str = Field(description="Which rule this verdict is about.", examples=["anonymised"])
    status: str = Field(description="pass · partial · fail · not_applicable.")
    confidence: float = Field(description="Judge's confidence, 0–1. Low values flag human review.")
    quote: str = Field(default="", description="Verbatim evidence from the brief (its own language).")
    note: str = Field(default="", description="≤8 words on what is there or missing.")
    weight: float = Field(description="This rule's share of the score (all weights sum to 100).")
    severity: str = Field(description="high · medium — editorial urgency, not score math.")
    gate: str | None = Field(
        None, description="If set, this rule is also a publish gate: 'pass' or 'not_fail' required."
    )


class GateOut(BaseModel):
    passed: bool = Field(description="False ⇒ decision is 'blocked', whatever the score says.")
    missing: list[str] = Field(description="Gate rules still unmet, by id.", examples=[["anonymised"]])
    contexts: list[str] = Field(
        default_factory=list, description="Policy contexts honoured on this call (audit trail)."
    )


class ScoreResponse(BaseModel):
    score: float | None = Field(None, description="0–100 weighted average. null if no rules applied.")
    band: str = Field(description="Human label for the score.", examples=["Directory-ready"])
    decision: str | None = Field(
        None, description="accepted · accepted_with_reservation · blocked — gate AND score, in code."
    )
    decision_label: str = Field(description="The decision, worded for humans.")
    gate: GateOut = Field(description="May it publish at all? Separate from the score on purpose.")
    verdicts: list[VerdictOut] = Field(description="One verdict per rule — the whole breakdown.")
    review_required: bool = Field(description="True when any verdict's confidence is low.")
    low_confidence: list[str] = Field(description="Rule ids behind review_required.")
    ruleset_version: str = Field(
        description="Exactly which bar judged this brief — re-runnable audit trail.",
        examples=["1.0.0+83107baec655"],
    )
    engine: str = Field(description="Engine version string.")
    judge: JudgeKind = Field(description="Which judge actually ran.")
    model: str | None = Field(None, description="Resolved LLM model; null for the mock judge.")
    cached: bool = Field(description="True if served from the verdict cache (same brief+ruleset+model).")


class ReviewOut(BaseModel):
    accepted: bool = Field(description="Did the verifier accept the suggestion?")
    reason: str = Field(default="", description="Verifier's objection when rejected.")


class Suggestion(BaseModel):
    rule_id: str = Field(description="The rule this insertion resolves.")
    label: str = Field(description="Menu label, ≤8 words.", examples=["Add a measurable target"])
    text: str = Field(description="One ready-to-paste sentence, tailored to the brief.")
    review: ReviewOut | None = Field(
        default=None, description="Verifier-loop verdict. null = verifier unavailable."
    )
    verifier_model: str | None = Field(default=None, description="Model that reviewed the suggestion.")


class ReferenceOut(BaseModel):
    tier: str = Field(description="standard · practice · encyclopedic — source authority.")
    title: str = Field(description="Source name.", examples=["WCAG 2.2 (W3C)"])
    locator: str = Field(description="What in the source anchors the rule.")
    url: str = Field(description="Link to the source.")


class RuleOut(BaseModel):
    id: str = Field(description="Canonical rule name, used in PRs and verdicts.", examples=["anonymised"])
    title: str = Field(description="One-line human title.")
    rationale: str = Field(description="Why the rule matters.")
    weight: float = Field(description="Share of the score (all weights sum to 100).")
    severity: str = Field(description="high · medium.")
    gate: str | None = Field(None, description="If set, also a publish-gate requirement.")
    criteria: str = Field(description="Exactly what the judge reads — the bar itself.")
    references: list[ReferenceOut] = Field(description="Pinned, human-verified sources.")


class RulesResponse(BaseModel):
    ruleset_version: str = Field(description="Version of the bar this response describes.")
    accept: float = Field(description="Score threshold for publishing without reservation.", examples=[85])
    budget_floor: int = Field(description="Directory engagement floor, in euros.", examples=[10000])
    gate: list[dict] = Field(description="The hard requirements and what each demands.")
    bands: list[dict] = Field(description="Descriptive score bands (labels only, no power).")
    rules: list[RuleOut] = Field(description="The whole ruleset — every rule is a contestable file.")


class ModelsResponse(BaseModel):
    default: str = Field(description="Model used when the request names none.")
    available: list[str] = Field(description="Allowlisted models for per-request override.")
    llm_configured: bool = Field(description="False ⇒ only the mock judge works here.")


class Health(BaseModel):
    status: str = Field(default="ok", description="Liveness.")
    release_version: str = Field(description="Deployed service release/tag version.")
    ruleset_version: str = Field(description="Bar currently loaded.")
    engine: str = Field(description="Engine version string.")
    llm_configured: bool = Field(description="Is a real judge available?")
