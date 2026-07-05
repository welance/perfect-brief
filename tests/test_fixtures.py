"""The immune system: every labelled brief must score in its band, reach its
decision, and match any pinned per-rule verdicts. This is what makes a ruleset
change reviewable — a PR that shifts the numbers has to move these too.
"""

import glob
import os

import pytest
import yaml

from perfect_brief import Status, aggregate, judge_all, load_bundled, loader
from perfect_brief.judge import MockJudge

RULES, CFG = load_bundled()
FIXTURES = sorted(glob.glob(os.path.join(loader.fixtures_dir(), "*.yaml")))


def _load(path):
    with open(path) as fh:
        return yaml.safe_load(fh)


@pytest.mark.parametrize("path", FIXTURES, ids=[os.path.basename(p) for p in FIXTURES])
def test_fixture(path):
    fx = _load(path)
    verdicts = judge_all(MockJudge(), RULES, fx["input"], fx.get("input_type", "brief"))
    res = aggregate(verdicts, RULES, CFG)

    lo, hi = fx["expected"]["min"], fx["expected"]["max"]
    assert lo <= res.score <= hi, f"{fx['id']}: score {res.score} not in [{lo},{hi}]"

    if "expected_decision" in fx:
        assert res.decision == fx["expected_decision"], (
            f"{fx['id']}: decision {res.decision} != {fx['expected_decision']}"
        )

    by = {v.rule_id: v.status for v in verdicts}
    for rid, want in (fx.get("expected_verdicts") or {}).items():
        assert by[rid] == Status(want), f"{fx['id']}: {rid} is {by[rid].value}, expected {want}"


def test_weights_sum_to_100():
    assert round(sum(r.weight for r in RULES.values())) == 100


def test_gate_rules_exist():
    ids = set(RULES)
    for g in CFG.gate:
        assert g["rule"] in ids
