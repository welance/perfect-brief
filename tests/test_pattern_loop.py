"""The offline pattern loop with the model stubbed — no network, no key, no cost.

The stub plays both roles (the controller prompt is told apart by its opening
line). One test runs the real harness on both engines; the rest stub it too.
"""

import hashlib
import json

import pytest

from brief_bar.patterns import CASES_PATH, CATALOGUE_PATH
from experiments import pattern_loop as loop

MODELS = [{"id": loop.MODEL, "pricing": {"prompt": "0.00000002394", "completion": "0.000000375"}}]
BASE = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
FAILING = {"ok": False, "invalid": [], "failures": [{"case": "x"}], "disagreements": [], "slow": []}
PASSING = {"ok": True, "invalid": [], "failures": [], "disagreements": [], "slow": []}


def _is_controller(prompt: str) -> bool:
    return prompt.startswith("You review")


def _variant(n: int) -> dict:
    cat = json.loads(json.dumps(BASE))
    cat["keywords"]["data"] = cat["keywords"]["data"] + [f"stub keyword {n}"]
    return cat


class Stub:
    """Scripted answers per role; records every call."""

    def __init__(self, proposals, reviews=None, cost=0.001):
        self.proposals, self.reviews, self.cost = list(proposals), list(reviews or []), cost
        self.calls = []

    def __call__(self, prompt, max_tokens):
        role = "controller" if _is_controller(prompt) else "proposer"
        self.calls.append(role)
        queue = self.reviews if role == "controller" else self.proposals
        answer = queue.pop(0) if queue else '{"add_cases": []}'
        return (answer if isinstance(answer, str) else json.dumps(answer)), self.cost


def _tracked():
    return hashlib.sha256(CATALOGUE_PATH.read_bytes() + CASES_PATH.read_bytes()).hexdigest()


def test_converges_on_the_real_harness_and_never_touches_tracked_files(tmp_path):
    before = _tracked()
    stub = Stub([{"catalogue": _variant(1), "why": "stub"}], [{"add_cases": [], "review": "fine"}])
    m = loop.run(call=stub, models=MODELS, out_dir=tmp_path)
    assert m["stop"] == "converged"
    assert m["best_ok"] and m["best_round"] == 1
    assert stub.calls == ["proposer", "controller"]
    assert m["model"]["id"] == "deepseek/deepseek-v4.1-flash"
    assert _tracked() == before
    assert "stub keyword 1" in (tmp_path / "proposal.diff").read_text()
    assert json.loads((tmp_path / "manifest.json").read_text())["spent_usd"] == pytest.approx(0.002)


def test_refuses_a_model_openrouter_does_not_list(tmp_path):
    stub = Stub([])
    m = loop.run(call=stub, models=[{"id": "deepseek/deepseek-v4-flash"}], out_dir=tmp_path,
                 evaluate=lambda *_: FAILING)  # fmt: skip
    assert "not listed" in m["stop"]
    assert stub.calls == []


def test_refuses_a_repriced_model(tmp_path):
    pricier = [{"id": loop.MODEL, "pricing": {"prompt": "0.000001", "completion": "0.000002"}}]
    m = loop.run(call=Stub([]), models=pricier, out_dir=tmp_path, evaluate=lambda *_: FAILING)
    assert "more than the pinned price" in m["stop"]


def test_budget_is_checked_before_the_call(tmp_path):
    stub = Stub([{"catalogue": _variant(1)}])
    m = loop.run(call=stub, models=MODELS, out_dir=tmp_path, budget_usd=0.000001, evaluate=lambda *_: FAILING)
    assert m["stop"].startswith("budget")
    assert stub.calls == []


def test_unknown_cost_stops_the_run(tmp_path):
    stub = Stub([{"catalogue": _variant(1)}], cost=None)
    m = loop.run(call=stub, models=MODELS, out_dir=tmp_path, evaluate=lambda *_: FAILING)
    assert "no cost" in m["stop"]
    assert stub.calls == ["proposer"]


def test_rounds_are_capped(tmp_path):
    stub = Stub([{"catalogue": _variant(n)} for n in range(20)])
    m = loop.run(call=stub, models=MODELS, out_dir=tmp_path, max_rounds=2, evaluate=lambda *_: FAILING)
    assert m["stop"] == "rounds"
    assert stub.calls == ["proposer", "controller"] * 2


def test_limits_cannot_be_raised_past_the_hard_caps(tmp_path):
    m = loop.run(call=Stub([]), models=[], out_dir=tmp_path, max_rounds=50, budget_usd=20,
                 evaluate=lambda *_: FAILING)  # fmt: skip
    assert m["limits"]["max_rounds"] == 8
    assert m["limits"]["budget_usd"] == 1.0


def test_two_unusable_answers_stop_the_run(tmp_path):
    stub = Stub(["not json", '{"why": "no catalogue"}'])
    m = loop.run(call=stub, models=MODELS, out_dir=tmp_path, evaluate=lambda *_: FAILING)
    assert m["stop"] == "invalid"
    assert m["best_round"] == 0


def test_a_repeated_catalogue_is_no_progress(tmp_path):
    stub = Stub([{"catalogue": BASE}])
    m = loop.run(call=stub, models=MODELS, out_dir=tmp_path, evaluate=lambda *_: FAILING)
    assert m["stop"] == "no-progress"


def test_controller_cases_are_marked_and_cannot_overwrite_labels(tmp_path):
    existing = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"][0]
    review = {
        "add_cases": [
            {"id": "ai-1", "locale": "it", "text": "Fax 06 1234 5678", "spans": [["phone", "06 1234 5678"]],
             "origin": "human"},
            {"id": existing["id"], "locale": "it", "text": "relabel", "spans": [["phone", "relabel"]]},
            {"id": "ai-bad-span", "locale": "it", "text": "abc", "spans": [["phone", "xyz"]]},
            {"id": "ai-bad-locale", "locale": "xx", "text": "abc", "spans": []},
        ]
    }  # fmt: skip
    stub = Stub([{"catalogue": _variant(1)}], [review])
    m = loop.run(call=stub, models=MODELS, out_dir=tmp_path, max_rounds=1, evaluate=lambda *_: FAILING)
    assert m["rounds"][0]["added_cases"] == ["ai-1"]
    out = json.loads((tmp_path / "best" / "cases.json").read_text())["cases"]
    added = [c for c in out if c["id"] == "ai-1"]
    assert added and added[0]["origin"] == "ai-proposed"
    assert next(c for c in out if c["id"] == existing["id"]) == existing


def test_out_dir_inside_the_package_is_refused(tmp_path):
    with pytest.raises(loop.Stop):
        loop.run(
            call=Stub([]), models=MODELS, out_dir=CATALOGUE_PATH.parent / "x", evaluate=lambda *_: PASSING
        )
