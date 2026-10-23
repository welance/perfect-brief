"""Bring your own model: the bar, without our judge.

The free surface hands a client everything its own model needs to judge a
brief — the rules, the exact judge prompt the service uses, the verdict
schema — and takes the verdicts back to aggregate them with the same engine
(`score.aggregate`) that scores on the service. No provider is called here,
ever: this module imports no client and holds no key.

What comes back is honest about where it came from. Verdicts written by a
model we did not run are **advisory**: the arithmetic is ours and identical,
the judgement is not. Results carry `evaluation_source: "client"` and can
never authorise publication on the welance/directory, which re-scores every
brief with its own judge.

Pure functions, no service dependencies (invariant 4).
"""

from __future__ import annotations

import json
import re
from typing import Any

from . import llm, patterns
from .score import Rule, ScoringConfig, Status, Verdict

CONTRACT = "pb-byo/1"
STATUSES = tuple(s.value for s in Status)
BRIEF_PLACEHOLDER = "{{BRIEF}}"
EVALUATION_SOURCE = "client"
ADVISORY_NOTICE = (
    "Client-judged and advisory. The verdicts were written by a model welance did not run, so "
    "this result is not a welance score and cannot authorise publication on the welance/directory: "
    "the directory re-scores every brief with its own judge before anything is published."
)
SEMANTIC_NOTICE = (
    "Deterministic checks only. They find contact details, stated budgets and timelines, data "
    "cues and missing sections by pattern; they do not judge meaning, so semantic coverage is "
    "INCOMPLETE. A brief can pass every check here and still fail the bar. Judge it with "
    "get_judge_prompt and your own model, then aggregate_verdicts."
)
MAX_QUOTE_WORDS = 15  # what the judge prompt asks for; longer quotes only warn


# ---- the bar, as data ------------------------------------------------------


def contexts(rules: dict[str, Rule], cfg: ScoringConfig) -> list[str]:
    """Every policy context tag a request may switch off (e.g. "directory")."""
    tags = {r.context for r in rules.values() if r.context}
    tags |= {g["context"] for g in cfg.gate if g.get("context")}
    return sorted(tags)


def active_contexts(directory_context: bool) -> list[str] | None:
    """None = every context active (the service default); [] = generic brief."""
    return None if directory_context else []


def rubric(rules: dict[str, Rule], cfg: ScoringConfig, version: str) -> dict[str, Any]:
    """The whole live catalogue plus the arithmetic that turns verdicts into a number."""
    return {
        "contract": CONTRACT,
        "ruleset_version": version,
        "rule_count": len(rules),
        "statuses": list(STATUSES),
        "status_scores": cfg.status_scores,
        "confidence_threshold": cfg.confidence_threshold,
        "accept": cfg.accept,
        "budget_floor": cfg.budget_floor,
        "bands": cfg.bands,
        "gate": cfg.gate,
        "gate_contexts": {
            "available": contexts(rules, cfg),
            "default": "all active (directory_context=true)",
            "generic": "directory_context=false drops every context-tagged rule from score and gate",
        },
        "rules": [
            {
                "id": r.id,
                "title": r.title,
                "rationale": r.rationale,
                "criteria": r.criteria.strip(),
                "weight": r.weight,
                "severity": r.severity,
                "gate": r.gate,
                "context": r.context,
                "how_to_pass": llm.FIXHINT.get(r.id, r.criteria.strip()),
                "pass_examples": list(r.pass_examples),
                "fail_examples": list(r.fail_examples),
                "references": [
                    {"tier": x.tier, "title": x.title, "locator": x.locator, "url": x.url}
                    for x in r.references
                ],
            }
            for r in rules.values()
        ],
    }


def verdict_schema(rules: dict[str, Rule]) -> dict[str, Any]:
    """JSON Schema for the array the client's model must return: one verdict per rule."""
    ids = list(rules)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Perfect Brief verdicts",
        "description": "One verdict per rule, exactly once each. The quote must be copied verbatim "
        "from the brief (an ellipsis may stand for words left out); empty when there is no evidence.",
        "type": "array",
        "minItems": len(ids),
        "maxItems": len(ids),
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["rule_id", "status", "confidence", "quote", "note"],
            "properties": {
                "rule_id": {"type": "string", "enum": ids},
                "status": {"type": "string", "enum": list(STATUSES)},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "quote": {"type": "string", "maxLength": 600},
                "note": {"type": "string", "maxLength": 200},
            },
        },
    }


def judge_prompt(rules: dict[str, Rule], cfg: ScoringConfig, brief: str | None) -> str:
    """The service judge's own prompt, word for word: the client grades against the same bar."""
    return llm.render_judge_prompt(rules, brief if brief else BRIEF_PLACEHOLDER, cfg.budget_floor)


# ---- the template ------------------------------------------------------------

# Section labels for the template, keyed by rule id. Rules not listed fall back
# to their title, so a new rule appears in the template without a code change.
_SECTION = {
    "clear-title": "Title",
    "problem-defined": "Problem",
    "users-identified": "Users",
    "success-metrics": "Success",
    "deliverables-concrete": "Deliverables",
    "scope-boundaries": "Out of scope",
    "budget-floor": "Budget",
    "timeline": "Timeline",
    "team-shape": "Team",
    "constraints-tech": "Constraints",
    "assumptions-risks": "Risks and assumptions",
    "data-compliance": "Data and compliance",
    "accessibility-considered": "Accessibility",
    "anonymised": None,  # not a section: a property of the whole text
}


def brief_template(rules: dict[str, Rule], cfg: ScoringConfig, version: str) -> dict[str, Any]:
    ordered = sorted(rules.values(), key=lambda r: (r.id != "clear-title", -r.weight, r.id))
    inputs = []
    lines = ["# <one specific line naming the product or the problem>", ""]
    for r in ordered:
        label = _SECTION.get(r.id, r.title)
        hint = llm.FIXHINT.get(r.id, r.criteria.strip())
        inputs.append(
            {
                "rule_id": r.id,
                "section": label,
                "required_for_gate": bool(r.gate),
                "context": r.context,
                "weight": r.weight,
                "what_to_write": hint,
            }
        )
        if label and r.id != "clear-title":
            lines += [f"## {label}", f"<!-- {r.id}: {hint} -->", ""]
    return {
        "contract": CONTRACT,
        "ruleset_version": version,
        "format": "markdown",
        "template": "\n".join(lines).rstrip() + "\n",
        "required_inputs": inputs,
        "notes": [
            "Write in any language; the bar grades meaning, not language.",
            "Replace every <…> and remove the comments before judging: placeholders read as missing.",
            f"For the welance/directory: no company, brand or person names, no emails, URLs or phone "
            f"numbers, and a budget of at least €{cfg.budget_floor:,}.",
        ],
    }


# ---- deterministic checks ---------------------------------------------------


def _first_line(brief: str) -> str:
    for line in brief.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _sections_found(brief: str) -> list[str]:
    low = brief.lower()
    found = []
    for rid, label in _SECTION.items():
        if label and rid != "clear-title":
            key = label.lower()
            if f"## {key}" in low or f"{key}:" in low:
                found.append(rid)
    return found


def _placeholders(brief: str) -> list[str]:
    out = []
    for rx in (r"<[^<>\n]{1,80}>", r"\[[^\[\]\n]{1,40}\](?!\()", r"\{\{[^{}\n]{1,40}\}\}"):
        out += [m.group(0) for m in re.finditer(rx, brief)]
    low = brief.lower()
    out += [w for w in ("lorem ipsum", "tbd", "todo") if w in low]
    return out[:10]


def check_brief(
    brief: str, rules: dict[str, Rule], cfg: ScoringConfig, version: str, directory_context: bool = True
) -> dict[str, Any]:
    """Structural and evidence checks a pattern can answer. Never a score, never a verdict."""
    cat = patterns.bundled()
    contacts = cat.contact_spans(brief)
    subjects = cat.subject_spans(brief)
    data_cues = cat.keyword_hits(brief, "data")
    compliance_cues = cat.keyword_hits(brief, "compliance")
    words = len(brief.split())
    title = _first_line(brief)
    sections = _sections_found(brief)
    holes = _placeholders(brief)

    def subject(kind: str) -> list[str]:
        return [s.text for s in subjects if s.subject == kind]

    checks: list[dict[str, Any]] = [
        {
            "id": "length",
            "rule_id": None,
            "outcome": "flag" if words < 80 else "found",
            "detail": f"{words} words"
            + (" — very short for a brief a team can build from" if words < 80 else ""),
            "evidence": [],
        },
        {
            "id": "title-line",
            "rule_id": "clear-title",
            "outcome": "found" if title and len(title) <= 120 else "not_found",
            "detail": "first non-empty line, read as the title"
            if title and len(title) <= 120
            else "no short first line to read as a title",
            "evidence": [title] if title else [],
        },
        {
            "id": "sections",
            "rule_id": None,
            "outcome": "found" if sections else "not_found",
            "detail": f"{len(sections)} template sections labelled (labels are English-only; an "
            "unlabelled section can still be present)",
            "evidence": sections,
        },
        {
            "id": "placeholders",
            "rule_id": None,
            "outcome": "flag" if holes else "found",
            "detail": "unfilled placeholders read as missing information" if holes else "none found",
            "evidence": holes,
        },
        {
            "id": "budget-stated",
            "rule_id": "budget-floor",
            "outcome": "found" if subject("budget") else "not_found",
            "detail": "a budget-labelled amount or range"
            + ("" if subject("budget") else " was not found; an unlabelled budget may still be there")
            + (
                f"; the directory floor is €{cfg.budget_floor:,} — the judge decides"
                if directory_context
                else ""
            ),
            "evidence": subject("budget"),
        },
        {
            "id": "timeline-stated",
            "rule_id": "timeline",
            "outcome": "found" if subject("timeline") else "not_found",
            "detail": "a timeline-labelled duration or deadline"
            + ("" if subject("timeline") else " was not found; an unlabelled one may still be there"),
            "evidence": subject("timeline"),
        },
        {
            "id": "contact-details",
            "rule_id": "anonymised",
            "outcome": "flag" if contacts else "found",
            "detail": (
                f"{len(contacts)} email/URL/phone span(s): a brief with any of these cannot pass "
                "anonymisation"
                if contacts
                else "no email, URL or phone found — names of companies, brands and people are NOT "
                "checked here"
            ),
            "evidence": [f"{c.kind}: {c.text}" for c in contacts][:10],
        },
        {
            "id": "data-cues",
            "rule_id": "data-compliance",
            "outcome": "flag" if data_cues and not compliance_cues else "found",
            "detail": (
                "personal-data cues without a compliance cue (lawful basis, DPA)"
                if data_cues and not compliance_cues
                else "data cues and compliance cues are consistent"
            ),
            "evidence": (data_cues + compliance_cues)[:10],
        },
    ]
    if not directory_context:
        checks = [c for c in checks if c["rule_id"] not in _context_rules(rules)]
        for c in checks:
            c["detail"] = c["detail"].replace(f"; the directory floor is €{cfg.budget_floor:,}", "")
    checked = {c["rule_id"] for c in checks if c["rule_id"]}
    return {
        "contract": CONTRACT,
        "ruleset_version": version,
        "evaluation_source": "deterministic",
        "semantic_coverage": "incomplete",
        "notice": SEMANTIC_NOTICE,
        "pattern_catalogue": cat.version,
        "checks": checks,
        "rules_with_a_deterministic_signal": sorted(checked),
        "rules_needing_a_model": [rid for rid in rules if rid not in checked],
        "score": None,
    }


def _context_rules(rules: dict[str, Rule]) -> set[str]:
    return {rid for rid, r in rules.items() if r.context}


# ---- client verdicts ---------------------------------------------------------


def _err(code: str, message: str, rule_id: str | None = None, index: int | None = None) -> dict[str, Any]:
    return {"code": code, "rule_id": rule_id, "index": index, "message": message}


def validate_verdicts(
    rules: dict[str, Rule], raw: Any, brief: str
) -> tuple[list[Verdict] | None, list[dict], list[dict], list[dict]]:
    """Validate a client's verdicts against the live ruleset.

    Returns (verdicts | None, errors, evidence_errors, warnings). Every problem
    is reported at once, so a client can fix its answer in one round. When
    there are none, the verdicts are produced by `llm.parse_judge` — the very
    parser that guards the service's own judge — so a client verdict reaches
    `aggregate` by the same door, or not at all.
    """
    errors: list[dict] = []
    evidence: list[dict] = []
    warnings: list[dict] = []
    if not isinstance(raw, list):
        return None, [_err("not_an_array", "verdicts must be a JSON array")], [], []

    seen: dict[str, dict] = {}
    for i, v in enumerate(raw):
        if not isinstance(v, dict):
            errors.append(_err("not_an_object", "a verdict must be an object", index=i))
            continue
        rid = v.get("rule_id")
        if not isinstance(rid, str) or rid not in rules:
            errors.append(_err("unknown_rule", f"unknown rule_id {rid!r} for this ruleset", index=i))
            continue
        if rid in seen:
            errors.append(_err("duplicate_rule", "rule judged more than once", rid, i))
            continue
        seen[rid] = v
        extra = set(v) - {"rule_id", "status", "confidence", "quote", "note"}
        if extra:
            errors.append(
                _err("unexpected_field", "unexpected field(s): " + ", ".join(sorted(extra)), rid, i)
            )
        status = v.get("status")
        if status not in STATUSES:
            errors.append(_err("invalid_status", f"status must be one of {', '.join(STATUSES)}", rid, i))
        conf = v.get("confidence")
        if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
            errors.append(_err("invalid_confidence", "confidence must be a number from 0 to 1", rid, i))
        quote, note = v.get("quote", ""), v.get("note", "")
        if not isinstance(quote, str) or not isinstance(note, str):
            errors.append(_err("non_text_evidence", "quote and note must be strings", rid, i))
            continue
        if len(quote) > 600 or len(note) > 200:
            errors.append(_err("evidence_too_long", "quote ≤ 600 and note ≤ 200 characters", rid, i))
            continue
        if quote and not llm.is_evidence(quote, brief):
            evidence.append(
                _err("quote_not_verbatim", "the quote is not in the brief (verbatim, in order)", rid, i)
            )
        elif status == "pass" and not quote and rid != "anonymised":
            warnings.append(_err("pass_without_evidence", "a pass with no quote is unsupported", rid, i))
        if quote and len(quote.split()) > MAX_QUOTE_WORDS:
            warnings.append(_err("long_quote", f"quotes should be under {MAX_QUOTE_WORDS} words", rid, i))

    for rid in rules:
        if rid not in seen:
            errors.append(_err("missing_rule", "no verdict for this rule; every rule must be judged", rid))

    if errors or evidence:
        return None, errors, evidence, warnings
    # Same parser, same integrity checks as the service judge. Anything the
    # loop above let through and this refuses is still a refusal.
    try:
        verdicts = llm.parse_judge(rules, json.dumps(raw), brief)
    except llm.JudgeUnparsable as exc:  # pragma: no cover - the loop above is stricter
        return None, [_err("unparsable", str(exc))], [], warnings
    return verdicts, [], [], warnings


def conflicts(verdicts: list[Verdict], brief: str, active: list[str] | None) -> list[dict]:
    """Where a client verdict contradicts something a pattern can see for certain."""
    out: list[dict] = []
    by = {v.rule_id: v for v in verdicts}
    directory_on = active is None or "directory" in active
    anon = by.get("anonymised")
    if directory_on and anon is not None and anon.status is Status.PASS:
        spans = patterns.contact_spans(brief)
        if spans:
            out.append(
                _err(
                    "anonymised_but_contacts",
                    "judged anonymised, yet the brief contains "
                    + ", ".join(f"{s.kind} '{s.text}'" for s in spans[:3]),
                    "anonymised",
                )
            )
    return out


def improvement_prompt(
    rules: dict[str, Rule],
    cfg: ScoringConfig,
    brief: str,
    verdicts: list[Verdict] | None,
    active: list[str] | None,
) -> str:
    """A working order for the client's own model to improve a brief, locally."""
    off = set() if active is None else {r.id for r in rules.values() if r.context and r.context not in active}
    gate_ids = [g["rule"] for g in cfg.gate if g["rule"] not in off]
    if verdicts:
        gaps = [v for v in verdicts if v.status in (Status.FAIL, Status.PARTIAL) and v.rule_id not in off]
        gaps.sort(key=lambda v: (v.rule_id not in gate_ids, -rules[v.rule_id].weight))
        targets = (
            "\n".join(
                f"- {v.rule_id} ({v.status.value}, weight {rules[v.rule_id].weight:g}"
                + (", GATE" if v.rule_id in gate_ids else "")
                + f"): {llm.FIXHINT.get(v.rule_id, rules[v.rule_id].criteria.strip())}"
                for v in gaps
            )
            or "- none: every rule passes or does not apply"
        )
        where = "These rules are failing or partial in the verdicts you already have, gate first:"
    else:
        ordered = sorted(
            (r for r in rules.values() if r.id not in off), key=lambda r: (r.id not in gate_ids, -r.weight)
        )
        targets = "\n".join(
            f"- {r.id} (weight {r.weight:g}" + (", GATE" if r.id in gate_ids else "") + f"): "
            f"{llm.FIXHINT.get(r.id, r.criteria.strip())}"
            for r in ordered
        )
        where = "No verdicts yet. Judge first (get_judge_prompt), then work through these, gate first:"
    return f"""Help me improve this digital product brief against the Perfect Brief bar, using your own model.
Nothing here calls welance's model; you do the writing, the bar's own code does the arithmetic.

Work in this order and do not skip steps:
1. If you have not yet: call `get_judge_prompt` with the brief, answer it yourself with the exact JSON
   it asks for, and send that JSON to `aggregate_verdicts` together with the brief and the ruleset_version.
2. Report the result plainly, and say that it is client-judged and advisory — never call it a welance score.
3. Fix the gate first: {", ".join(gate_ids)}. A brief that fails the gate is blocked at any score.
4. {where}
{targets}
5. For each gap: quote what the brief says now, name the criterion it misses, and propose a rewrite of
   that part in the brief's own domain and language — no placeholders, no brackets, no invented facts.
   Ask me for any fact you would otherwise have to invent (a budget, a date, a metric).
6. After my edits, judge again and aggregate again. Stop when the decision is "accepted" or when the
   remaining gaps are ones I choose not to fix.

Rules of engagement:
- Never invent, estimate or round a score. Numbers come from `aggregate_verdicts` or not at all.
- Quotes in verdicts must be copied verbatim from the brief, or aggregation refuses them.
- Keep my voice. You are raising the floor, not rewriting the brief as yours.
- To publish on the welance/directory, the directory scores the brief again with its own judge.

The brief:

{brief or "(paste the brief here)"}"""
