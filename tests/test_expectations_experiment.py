import json
import runpy
from pathlib import Path

import jsonschema
import pytest
import yaml

from brief_bar import llm, load_bundled

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = runpy.run_path(str(ROOT / "experiments/expectations_v1.py"))


def test_variant_changes_only_declared_criteria_and_preserves_gate():
    baseline, criteria, candidate, cfg = EXPERIMENT["load_variant"]()
    assert len(candidate) == 15
    assert sum(r.weight for r in candidate.values()) == pytest.approx(100)
    assert sum(r.weight for r in criteria.values()) == pytest.approx(100)
    changed = {rid for rid in baseline if baseline[rid].criteria != criteria[rid].criteria}
    assert changed == {"scope-boundaries", "assumptions-risks"}
    assert cfg.gate == load_bundled()[1].gate
    assert candidate["scope-resource-alignment"].gate is None
    assert candidate["scope-resource-alignment"].context is None
    assert len(load_bundled()[0]) == 14
    assert EXPERIMENT["version"]().startswith("1.2.0-expectations.1+")


def test_candidate_files_match_rule_schema():
    schema = json.loads((ROOT / "brief_bar/schemas/rule.schema.json").read_text())
    for path in (EXPERIMENT["DATA"] / "rules").glob("*.yaml"):
        jsonschema.validate(yaml.safe_load(path.read_text()), schema)


def test_new_rule_is_scored_in_both_contexts_with_no_hidden_cap():
    _, _, rules, _ = EXPERIMENT["load_variant"]()
    raw = [{"rule_id": rid, "status": "pass", "confidence": 1, "quote": "", "note": ""} for rid in rules]
    raw[-1]["status"] = "fail"
    result = EXPERIMENT["evaluate"](json.dumps(raw), "source")
    original_weights = result["results"]["revised_criteria_original_weights"]
    candidate = result["results"]["candidate_with_new_rule"]
    assert original_weights["directory"]["score"] == 100
    assert original_weights["generic"]["score"] == 100
    assert candidate["directory"]["score"] == 90
    assert candidate["generic"]["score"] == pytest.approx(100 * 72.9 / 82.9, abs=0.01)


def test_incomplete_candidate_verdicts_are_refused():
    with pytest.raises(llm.JudgeUnparsable):
        EXPERIMENT["evaluate"]("[]", "source")
