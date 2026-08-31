"""
score.py — the deterministic half.

The LLM produces a per-rule verdict (status + evidence + confidence). This
module owns everything else, deterministically:

  - the SCORE: a weighted average over applicable rules (0-100), renormalised
    when rules are not_applicable, plus a descriptive band label.
  - the GATE: hard requirements that must hold to publish at all. Separate from
    the score (this replaces the old severity-cap mechanism).
  - the DECISION: blocked / reserved / accepted.

No model call here. Same verdicts + same scoring.yaml -> identical output.
"""

from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from enum import Enum

import yaml


class Status(str, Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class Reference:
    tier: str
    title: str
    locator: str
    url: str


@dataclass(frozen=True)
class Finding:
    quote: str
    note: str


@dataclass(frozen=True)
class Verdict:
    rule_id: str
    status: Status
    confidence: float
    findings: tuple[Finding, ...] = ()


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    rationale: str
    weight: float
    severity: str
    criteria: str
    gate: str | None = None  # None | "not_fail" | "pass"
    context: str | None = None  # e.g. "directory": rule drops out when the context is off
    applies_to: tuple[str, ...] = ()
    pass_examples: tuple[str, ...] = ()
    fail_examples: tuple[str, ...] = ()
    references: tuple[Reference, ...] = ()
    version: int = 1

    def applies(self, input_type: str) -> bool:
        return not self.applies_to or input_type in self.applies_to


@dataclass
class ScoringConfig:
    status_scores: dict[str, float]
    confidence_threshold: float
    abstain_when_no_rules_apply: bool
    budget_floor: int
    gate: list[dict]
    bands: list[dict]
    accept: float
    labels: dict[str, str]


def load_rules(rules_dir: str) -> dict[str, Rule]:
    rules: dict[str, Rule] = {}
    for path in sorted(glob.glob(os.path.join(rules_dir, "*.yaml"))):
        with open(path) as fh:
            d = yaml.safe_load(fh)
        refs = tuple(
            Reference(r.get("tier", "practice"), r["title"], r.get("locator", ""), r.get("url", ""))
            for r in (d.get("references") or [])
        )
        rule = Rule(
            id=d["id"],
            title=d["title"],
            rationale=d["rationale"],
            weight=float(d["weight"]),
            severity=d["severity"],
            criteria=d["criteria"],
            gate=d.get("gate"),
            context=d.get("context"),
            applies_to=tuple(d.get("applies_to") or ()),
            pass_examples=tuple(d.get("pass_examples") or ()),
            fail_examples=tuple(d.get("fail_examples") or ()),
            references=refs,
            version=int(d.get("version", 1)),
        )
        if rule.id in rules:
            raise ValueError(f"duplicate rule id: {rule.id}")
        rules[rule.id] = rule
    return rules


def load_config(path: str) -> ScoringConfig:
    with open(path) as fh:
        d = yaml.safe_load(fh)
    pub = d["publication"]
    return ScoringConfig(
        status_scores=d["status_scores"],
        confidence_threshold=float(d["confidence_threshold"]),
        abstain_when_no_rules_apply=bool(d["abstain_when_no_rules_apply"]),
        budget_floor=int(d.get("budget_floor", 0)),
        gate=d.get("gate") or [],
        bands=d.get("bands") or [],
        accept=float(pub["accept"]),
        labels=pub["labels"],
    )


@dataclass
class RuleContribution:
    rule_id: str
    status: Status
    weight: float
    unit_score: float
    weighted: float


@dataclass
class ScoreBreakdown:
    score: float | None
    band: str
    decision: str | None  # accepted | reserved | blocked | None
    decision_label: str
    gate_passed: bool
    gate_missing: list[str]
    gate_contexts: list[str] = field(default_factory=list)  # context tags honored
    review_required: bool = False
    contributions: list[RuleContribution] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    low_confidence: list[str] = field(default_factory=list)


def _band(score: float | None, cfg: ScoringConfig) -> str:
    if score is None:
        return "—"
    for b in cfg.bands:
        if score >= b["min"]:
            return b["label"]
    return cfg.bands[-1]["label"] if cfg.bands else "—"


def _gate(
    verdicts: dict[str, Status], cfg: ScoringConfig, contexts: frozenset[str] | None
) -> tuple[bool, list[str], list[str]]:
    """contexts=None means every context tag is active (the service default);
    otherwise a context-tagged requirement applies only if its tag is listed.
    Returns (passed, missing rule ids, context tags honored)."""
    missing: list[str] = []
    active: set[str] = set()
    for req in cfg.gate:
        tag = req.get("context")
        if tag is not None:
            if contexts is not None and tag not in contexts:
                continue
            active.add(tag)
        st = verdicts.get(req["rule"], Status.FAIL)
        ok = (st is Status.PASS) if req["require"] == "pass" else (st in (Status.PASS, Status.PARTIAL))
        if not ok:
            missing.append(req["rule"])
    return (len(missing) == 0, missing, sorted(active))


def aggregate(
    verdicts: list[Verdict],
    rules: dict[str, Rule],
    cfg: ScoringConfig,
    contexts: list[str] | frozenset[str] | None = None,
) -> ScoreBreakdown:
    contributions: list[RuleContribution] = []
    excluded: list[str] = []
    low_conf: list[str] = []
    numer = 0.0
    denom = 0.0
    by_status = {v.rule_id: v.status for v in verdicts}
    ctx = None if contexts is None else frozenset(contexts)

    for v in verdicts:
        rule = rules[v.rule_id]
        if rule.context and ctx is not None and rule.context not in ctx:
            # the rule is consumer policy for a deactivated context: it
            # neither scores nor gates, and the average renormalises
            excluded.append(v.rule_id)
            continue
        if v.confidence < cfg.confidence_threshold:
            low_conf.append(v.rule_id)
        if v.status is Status.NOT_APPLICABLE:
            excluded.append(v.rule_id)
            continue
        unit = cfg.status_scores[v.status.value]
        weighted = rule.weight * unit
        numer += weighted
        denom += rule.weight
        contributions.append(RuleContribution(v.rule_id, v.status, rule.weight, unit, weighted))

    gate_passed, gate_missing, gate_contexts = _gate(by_status, cfg, ctx)

    if denom == 0:
        score = None if cfg.abstain_when_no_rules_apply else 100.0
        decision = "blocked" if not gate_passed else None
        label = cfg.labels.get("blocked", "") if not gate_passed else "No applicable rules"
        return ScoreBreakdown(
            score=score,
            band=_band(score, cfg),
            decision=decision,
            decision_label=label,
            gate_passed=gate_passed,
            gate_missing=gate_missing,
            gate_contexts=gate_contexts,
            review_required=bool(low_conf),
            contributions=contributions,
            excluded=excluded,
            low_confidence=low_conf,
        )

    score = round(100.0 * numer / denom, 2)
    band = _band(score, cfg)
    if not gate_passed:
        decision, label = "blocked", cfg.labels["blocked"]
    elif score >= cfg.accept:
        decision, label = "accepted", cfg.labels["accepted"]
    else:
        decision, label = "reserved", cfg.labels["reserved"]
    return ScoreBreakdown(
        score=score,
        band=band,
        decision=decision,
        decision_label=label,
        gate_passed=gate_passed,
        gate_missing=gate_missing,
        gate_contexts=gate_contexts,
        review_required=bool(low_conf),
        contributions=contributions,
        excluded=excluded,
        low_confidence=low_conf,
    )
