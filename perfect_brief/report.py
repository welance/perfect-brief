"""
report.py — what the submitter reads.

Score (a progress bar toward publication) + its band, the publish decision and —
if blocked — exactly which hard requirements are unmet, then what's strong and
what would raise it, each pointing at its rule and an authoritative source.

  python report.py "your brief text..."
"""

from __future__ import annotations

import os
import sys

from .judge import MockJudge, judge_all
from .score import Status, aggregate, load_config, load_rules

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "https://github.com/welance/perfect-brief/blob/main/rules"


def _cite(rule):
    if not rule.references:
        return f"rule: {rule.id}"
    r = rule.references[0]
    return f"rule: {rule.id} ({REPO}/{rule.id}.yaml) · source: {r.title} — {r.locator}"


def report(text: str, itype: str = "brief") -> None:
    rules = load_rules(os.path.join(HERE, "rules"))
    cfg = load_config(os.path.join(HERE, "scoring.yaml"))
    verdicts = judge_all(MockJudge(), rules, text, itype)
    res = aggregate(verdicts, rules, cfg)

    bar = "" if res.score is None else "█" * round(res.score / 5) + "·" * (20 - round(res.score / 5))
    print("\n" + "=" * 66)
    print(f"  PERFECT BRIEF SCORE   {res.score}/100   {res.band}   [{bar}]")
    print(f"  {res.decision_label.upper()}")
    if not res.gate_passed:
        names = ", ".join(rules[m].title for m in res.gate_missing)
        print(f"  ✗ hard requirements unmet: {names}")
    if res.review_required:
        print(f"  ⚑ flagged for human review: low confidence on {', '.join(res.low_confidence)}")
    print("=" * 66)

    strong = [v for v in verdicts if v.status is Status.PASS]
    if strong:
        print("\nWHAT'S STRONG")
        for v in strong:
            r = rules[v.rule_id]
            mark = "★✓" if r.gate else " ✓"
            print(f" {mark} {r.title}")
            print(f"      {v.findings[0].note}.")
            print(f"      {_cite(r)}")

    gaps = [v for v in verdicts if v.status in (Status.PARTIAL, Status.FAIL)]
    if gaps:
        print("\nWHAT WOULD RAISE IT")
        for v in sorted(gaps, key=lambda x: -rules[x.rule_id].weight):
            r = rules[v.rule_id]
            mark = "◐" if v.status is Status.PARTIAL else "✗"
            gate = " ★gate" if r.gate else ""
            print(f"  {mark} {r.title}  (worth {int(r.weight)} pts, {r.severity}{gate})")
            print(f"      {v.findings[0].note}: {v.findings[0].quote}")
            print(f"      {_cite(r)}")

    na = [v for v in verdicts if v.status is Status.NOT_APPLICABLE]
    if na:
        print(f"\nNOT APPLICABLE: {', '.join(v.rule_id for v in na)}")
    print()


def _cli() -> None:
    text = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "We want to build a modern, scalable platform that delights everyone."
    )
    report(text)


if __name__ == "__main__":
    _cli()
