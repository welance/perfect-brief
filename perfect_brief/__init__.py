"""perfect_brief — the open ruleset + deterministic engine.

The scoring half (this package) is decoupled from the LLM half by one seam:
a judge returns a per-rule verdict; code owns the weighting, the gate, and the
decision. Same verdicts + same ruleset_version -> identical output.

    from perfect_brief import load_bundled, score
    rules, cfg = load_bundled()
    breakdown, verdicts = score("my brief...", rules, cfg, MockJudge())
"""

from __future__ import annotations

from . import llm, loader
from .judge import LLMJudge, MockJudge, judge_all, parse_verdict, render_prompt
from .score import (
    Finding,
    Reference,
    Rule,
    ScoreBreakdown,
    ScoringConfig,
    Status,
    Verdict,
    aggregate,
    load_config,
    load_rules,
)

__all__ = [
    "load_bundled",
    "score",
    "aggregate",
    "load_rules",
    "load_config",
    "MockJudge",
    "LLMJudge",
    "judge_all",
    "render_prompt",
    "parse_verdict",
    "Rule",
    "Verdict",
    "Status",
    "Finding",
    "Reference",
    "ScoreBreakdown",
    "ScoringConfig",
    "loader",
    "llm",
]


def load_bundled() -> tuple[dict[str, Rule], ScoringConfig]:
    """Load the ruleset + scoring config that ship with the package."""
    return load_rules(loader.rules_dir()), load_config(loader.scoring_path())


def score(text, rules, cfg, judge, itype: str = "brief"):
    """Convenience: judge every applicable rule, then aggregate. Returns (breakdown, verdicts)."""
    verdicts = judge_all(judge, rules, text, itype)
    return aggregate(verdicts, rules, cfg), verdicts
