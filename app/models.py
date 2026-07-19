"""API request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

JudgeKind = Literal["mock", "llm"]


class ScoreRequest(BaseModel):
    brief: str = Field(..., description="The brief text to score.")
    locale: str = Field("en-GB", description="Display locale (also steers LLM output language).")
    judge: JudgeKind | None = Field(None, description="Override the default judge for this call.")
    model: str | None = Field(
        None, description="LLM model for the judge; must be in GET /v1/models. Default: server default."
    )
    gate_contexts: list[str] | None = Field(
        None,
        description=(
            "Active gate contexts. Context-tagged gate requirements (anonymised -> 'directory') "
            "apply only if listed. Default (null): all contexts active. Pass [] to score a "
            "generic brief without the Directory's blind-noticeboard requirement."
        ),
    )


class SuggestRequest(BaseModel):
    brief: str
    rule_id: str
    locale: str = "en-GB"
    model: str | None = None


class SuggestAllRequest(BaseModel):
    brief: str
    rule_ids: list[str] | None = Field(None, description="Defaults to every failing/partial rule.")
    locale: str = "en-GB"
    model: str | None = None


class VerdictOut(BaseModel):
    rule_id: str
    status: str
    confidence: float
    quote: str = ""
    note: str = ""
    weight: float
    severity: str
    gate: str | None = None


class GateOut(BaseModel):
    passed: bool
    missing: list[str]
    contexts: list[str] = []  # context tags honored for this call (audit trail)


class ScoreResponse(BaseModel):
    score: float | None
    band: str
    decision: str | None
    decision_label: str
    gate: GateOut
    verdicts: list[VerdictOut]
    review_required: bool
    low_confidence: list[str]
    ruleset_version: str
    engine: str
    judge: JudgeKind
    model: str | None = None  # resolved LLM model; null for the mock judge
    cached: bool


class ReviewOut(BaseModel):
    accepted: bool
    reason: str = ""


class Suggestion(BaseModel):
    rule_id: str
    label: str
    text: str
    # Verifier-loop verdict (None = review unavailable, e.g. verifier down)
    review: ReviewOut | None = None
    verifier_model: str | None = None


class ReferenceOut(BaseModel):
    tier: str
    title: str
    locator: str
    url: str


class RuleOut(BaseModel):
    id: str
    title: str
    rationale: str
    weight: float
    severity: str
    gate: str | None = None
    criteria: str
    references: list[ReferenceOut]


class RulesResponse(BaseModel):
    ruleset_version: str
    accept: float
    budget_floor: int
    gate: list[dict]
    bands: list[dict]
    rules: list[RuleOut]


class ModelsResponse(BaseModel):
    default: str
    available: list[str]
    llm_configured: bool


class Health(BaseModel):
    status: str = "ok"
    ruleset_version: str
    engine: str
    llm_configured: bool
