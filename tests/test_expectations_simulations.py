"""Offline safeguards for the experiment; these do not validate a judge's accuracy."""

import json
from copy import deepcopy

import pytest

from brief_bar.score import Status, Verdict
from experiments.expectations_simulations import (
    CRITICAL,
    FACTS,
    cases,
    parse_structured,
    prompt,
    simulate_aggregation,
)
from experiments.expectations_v1 import load_variant

SOURCE = "The budget is indicative. Scope will be agreed before work."


def response(statuses=("pass", "pass", "pass"), kinds=("none", "none", "none")):
    return {
        "facts": {name: {"summary": "A source-backed fact", "quotes": [SOURCE]} for name in FACTS},
        "verdicts": [
            {"rule_id": rid, "status": status, "kind": kind, "confidence": 0.9,
             "evidence": ["The budget is indicative."],
             "counterevidence": ["Scope will be agreed before work."], "reason": "Source-backed rationale"}
            for rid, status, kind in zip(CRITICAL, statuses, kinds, strict=True)
        ],
    }


def baseline():
    rules, _, _, _ = load_variant()
    return [Verdict(rid, Status.PASS, 1) for rid in rules]


def parse(value):
    return parse_structured(json.dumps(value), SOURCE)


def test_parser_preserves_verified_support_and_counterevidence():
    value = response()
    assert parse(value) == value


@pytest.mark.parametrize("location", ["fact", "evidence", "counterevidence"])
def test_unverifiable_quotes_are_rejected_in_every_evidence_channel(location):
    value = response()
    if location == "fact":
        value["facts"]["resources"]["quotes"] = ["The agreed budget is EUR 100,000."]
    else:
        value["verdicts"][0][location] = ["The agreed budget is EUR 100,000."]
    with pytest.raises(ValueError, match="unverifiable quote"):
        parse(value)


@pytest.mark.parametrize("field", ["engagement", "resources", "schedule", "dependencies", "decision_path"])
def test_incomplete_fact_extraction_is_rejected(field):
    value = response()
    del value["facts"][field]
    with pytest.raises(ValueError, match="facts"):
        parse(value)


def test_missing_duplicate_and_unknown_criteria_are_rejected():
    missing = response()
    missing["verdicts"].pop()
    duplicate = response()
    duplicate["verdicts"][1]["rule_id"] = CRITICAL[0]
    unknown = response()
    unknown["verdicts"][1]["rule_id"] = "invented-rule"
    for value in [missing, duplicate, unknown]:
        with pytest.raises(ValueError):
            parse(value)


def test_pass_requires_positive_evidence_even_if_counterevidence_exists():
    value = response()
    value["verdicts"][0]["evidence"] = []
    with pytest.raises(ValueError, match="pass without evidence"):
        parse(value)


def test_missing_information_can_be_reported_without_inventing_quotes():
    value = response(("partial", "pass", "pass"), ("missing", "none", "none"))
    value["verdicts"][0]["evidence"] = []
    value["verdicts"][0]["counterevidence"] = []
    value["facts"]["engagement"]["quotes"] = []
    assert parse(value) == value


def test_contradiction_requires_two_quoted_sides():
    value = response(("pass", "pass", "fail"), ("none", "none", "contradiction"))
    value["verdicts"][2]["counterevidence"] = []
    with pytest.raises(ValueError, match="two quoted sides"):
        parse(value)


@pytest.mark.parametrize("confidence", [True, -0.01, 1.01, "0.9", None, float("nan")])
def test_invalid_confidence_is_rejected(confidence):
    value = response()
    value["verdicts"][0]["confidence"] = confidence
    with pytest.raises(ValueError, match="confidence"):
        parse(value)


@pytest.mark.parametrize("status,kind", [("pass", "missing"), ("partial", "none"), ("fail", "none")])
def test_inconsistent_status_and_kind_is_rejected(status, kind):
    value = response()
    value["verdicts"][0].update(status=status, kind=kind)
    with pytest.raises(ValueError, match="inconsistent"):
        parse(value)


def test_model_supplied_score_and_caps_cannot_change_aggregation():
    value = response(("pass", "partial", "partial"), ("none", "ambiguity", "ambiguity"))
    expected = simulate_aggregation(baseline(), parse(value))
    poisoned = deepcopy(value)
    poisoned.update(score=2, cap=1, foundation_axis=0)
    for verdict in poisoned["verdicts"]:
        verdict.update(score=0, weight=10000)
    assert simulate_aggregation(baseline(), parse(poisoned)) == expected


@pytest.mark.parametrize(
    "statuses,kinds,cap,foundation",
    [
        (("pass", "pass", "pass"), ("none", "none", "none"), 100, 100),
        (("pass", "pass", "partial"), ("none", "none", "ambiguity"), 67, 83.33),
        (("pass", "partial", "partial"), ("none", "ambiguity", "ambiguity"), 67, 66.67),
        (("pass", "pass", "fail"), ("none", "none", "contradiction"), 44, 66.67),
        (("pass", "pass", "fail"), ("none", "none", "missing"), 67, 66.67),
    ],
)
def test_caps_and_critical_axis_are_distinct_policies(statuses, kinds, cap, foundation):
    result = simulate_aggregation(baseline(), parse(response(statuses, kinds)))
    for context in ("generic", "directory"):
        scores = result[context]
        assert scores["cap"] == cap
        assert scores["foundation_axis"] == foundation
        assert scores["with_cap"] == min(scores["weighted"]["score"], cap)
        assert scores["with_foundation_ceiling"] == pytest.approx(
            min(scores["weighted"]["score"], foundation), abs=0.01
        )


def test_aggregation_rejects_missing_noncritical_baseline_verdict():
    incomplete = [v for v in baseline() if v.rule_id != "team-shape"]
    with pytest.raises(ValueError, match="incomplete combined verdicts"):
        simulate_aggregation(incomplete, parse(response()))


@pytest.mark.parametrize("case_id", ["bounded_build", "discovery", "supplier_quote", "fixed_assessment"])
def test_legitimate_engagements_have_no_cap_if_judged_clear(case_id):
    case = next(item for item in cases() if item["id"] == case_id)
    assert set(case["expected"].values()) == {"pass"}
    result = simulate_aggregation(baseline(), parse(response(tuple(case["expected"][rid] for rid in CRITICAL))))
    assert result["generic"]["with_cap"] == 100
    assert result["generic"]["with_foundation_ceiling"] == 100


def test_expected_labels_and_case_metadata_do_not_leak_into_prompts():
    for case in cases():
        for arm in ("baseline", "flat", "structured"):
            rendered = prompt(arm, case["text"])
            assert case["text"] in rendered
            assert case["purpose"] not in rendered
            assert json.dumps(case["expected"]) not in rendered


def test_irrelevant_detail_and_translation_keep_expected_labels():
    by_id = {case["id"]: case for case in cases()}
    expected = by_id["generic_confirmation"]["expected"]
    for key in ("irrelevant_check", "verbose_irrelevant_check", "italian_confirmation"):
        assert by_id[key]["expected"] == expected
