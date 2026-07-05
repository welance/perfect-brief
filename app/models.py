"""API request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

JudgeKind = Literal["mock", "llm"]


class ScoreRequest(BaseModel):
    brief: str = Field(..., description="The brief text to score.")
    locale: str = Field("en-GB", description="Display locale (also steers LLM output language).")
    judge: JudgeKind | None = Field(None, description="Override the default judge for this call.")


class SuggestRequest(BaseModel):
    brief: str
    rule_id: str
    locale: str = "en-GB"


class SuggestAllRequest(BaseModel):
    brief: str
    rule_ids: list[str] | None = Field(None, description="Defaults to every failing/partial rule.")
    locale: str = "en-GB"


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
    cached: bool


class Suggestion(BaseModel):
    rule_id: str
    label: str
    text: str


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


class Health(BaseModel):
    status: str = "ok"
    ruleset_version: str
    engine: str
    llm_configured: bool
