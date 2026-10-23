"""Bring your own model: the free contract at /v1/byo.

Four promises, each held here:
1. No provider call, ever — not with a key configured, not with a key sent.
2. Same verdicts, same number: client verdicts aggregate exactly as the
   service's own judge's verdicts do (every fixture, both contexts).
3. A forged or malformed answer gets no score, and every problem is named.
4. A client-judged result is advisory. It never claims authority, and the
   authoritative /v1/score cannot be fed verdicts from outside.
"""

from __future__ import annotations

import glob
import os
import re

import pytest
import yaml

from app import byo as service
from app import llm_client, scorer
from brief_bar import aggregate, byo, judge_all, llm, load_bundled, loader
from brief_bar.judge import MockJudge

RULES, CFG = load_bundled()
FIXTURES = sorted(glob.glob(os.path.join(loader.fixtures_dir(), "**", "*.yaml"), recursive=True))
ACCEPTED = yaml.safe_load(open(os.path.join(loader.fixtures_dir(), "0003-accepted.yaml")))["input"]
FIELDS = ("rule_id", "status", "confidence", "quote", "note")


def client_verdicts(brief: str) -> list[dict]:
    """What a client model might send: the mock judge's statuses, honest (empty) quotes."""
    return [
        {"rule_id": v.rule_id, "status": v.status.value, "confidence": v.confidence, "quote": "", "note": ""}
        for v in judge_all(MockJudge(), RULES, brief, "brief")
    ]


def verbatim_verdicts(brief: str) -> list[dict]:
    """All-pass verdicts whose quotes really are in the brief."""
    words = " ".join(brief.split()[:4])
    return [
        {"rule_id": rid, "status": "pass", "confidence": 0.9, "quote": words, "note": "present"}
        for rid in RULES
    ]


@pytest.fixture
def no_provider(monkeypatch):
    """A configured provider that fails the test if anything reaches it."""
    calls: list[str] = []

    async def complete(*args, **kwargs):
        calls.append("complete")
        raise AssertionError("a BYO path called the provider")

    monkeypatch.setattr(llm_client, "complete", complete)
    monkeypatch.setattr(llm_client, "configured", lambda: True)
    return calls


# --- 1. zero provider calls -------------------------------------------------------


def test_every_byo_route_runs_without_a_provider_call(client, no_provider):
    key = {"x-llm-key": "sk-or-should-never-be-used"}
    version = client.get("/v1/byo/rules", headers=key).json()["ruleset_version"]
    assert client.get("/v1/byo/template", headers=key).status_code == 200
    assert client.get("/v1/byo/status", headers=key).json()["provider_calls"] == 0
    for path, body in [
        ("/v1/byo/judge-prompt", {"brief": ACCEPTED}),
        ("/v1/byo/judge-prompt", {}),
        ("/v1/byo/check", {"brief": ACCEPTED}),
        ("/v1/byo/improvement-prompt", {"brief": ACCEPTED, "verdicts": client_verdicts(ACCEPTED)}),
        (
            "/v1/byo/aggregate",
            {"brief": ACCEPTED, "verdicts": client_verdicts(ACCEPTED), "ruleset_version": version},
        ),
    ]:
        r = client.post(path, json=body, headers=key)
        assert r.status_code == 200, (path, r.text[:300])
    assert no_provider == []


def test_the_byo_modules_cannot_reach_a_provider():
    """Not by discipline: the modules do not import a client at all."""
    root = os.path.join(os.path.dirname(__file__), "..")
    for rel in ("brief_bar/byo.py", "app/byo.py"):
        src = open(os.path.join(root, rel), encoding="utf-8").read()
        imports = "\n".join(line for line in src.splitlines() if re.match(r"\s*(from|import) ", line))
        for banned in (
            "llm_client",
            "anthropic",
            "httpx",
            "openai",
            "openrouter",
            "scorer.score",
            "requests",
        ):
            assert banned not in imports, (rel, banned)


def test_status_says_there_is_no_fallback(client):
    s = client.get("/v1/byo/status").json()
    assert s["llm_fallback"] is False and s["provider_calls"] == 0
    assert s["mode"] == "bring-your-own-model"


# --- 2. identical math --------------------------------------------------------------


@pytest.mark.parametrize("path", FIXTURES, ids=[os.path.relpath(p, loader.fixtures_dir()) for p in FIXTURES])
@pytest.mark.parametrize("directory", [True, False])
def test_client_verdicts_aggregate_exactly_like_the_engine(path, directory):
    fx = yaml.safe_load(open(path, encoding="utf-8"))
    brief = fx["input"]
    engine = aggregate(judge_all(MockJudge(), RULES, brief, "brief"), RULES, CFG, None if directory else [])
    out = service.aggregate_payload(brief, client_verdicts(brief), scorer.version(), directory)
    assert out["valid"], (out["errors"], out["evidence_errors"])
    res = out["result"]
    assert res["score"] == engine.score
    assert res["band"] == engine.band
    assert res["decision"] == engine.decision
    assert res["gate"] == {
        "passed": engine.gate_passed,
        "missing": engine.gate_missing,
        "contexts": engine.gate_contexts,
    }
    assert res["low_confidence"] == engine.low_confidence


@pytest.mark.parametrize("name", ["0001-weak.yaml", "0003-accepted.yaml", "0004-blocked-brand.yaml"])
def test_same_verdicts_through_the_api_give_the_api_number(client, name):
    brief = yaml.safe_load(open(os.path.join(loader.fixtures_dir(), name)))["input"]
    server = client.post("/v1/score", json={"brief": brief, "judge": "mock"}).json()
    sent = [{k: (v[k] if k != "quote" else "") for k in FIELDS} for v in server["verdicts"]]
    mine = client.post(
        "/v1/byo/aggregate",
        json={"brief": brief, "verdicts": sent, "ruleset_version": server["ruleset_version"]},
    ).json()["result"]
    for k in ("score", "band", "decision", "gate", "review_required", "low_confidence"):
        assert mine[k] == server[k], k


def test_the_client_judge_prompt_is_the_service_prompt(client):
    out = client.post("/v1/byo/judge-prompt", json={"brief": ACCEPTED}).json()
    assert out["prompt"] == llm.render_judge_prompt(scorer.rules(), ACCEPTED, scorer.cfg().budget_floor)
    assert out["rule_ids"] == list(scorer.rules())
    schema = out["verdict_schema"]
    assert schema["minItems"] == schema["maxItems"] == len(scorer.rules())
    assert schema["items"]["properties"]["rule_id"]["enum"] == list(scorer.rules())
    template = client.post("/v1/byo/judge-prompt", json={}).json()
    assert template["placeholder"] == "{{BRIEF}}" and "{{BRIEF}}" in template["prompt"]


def test_the_verdict_schema_accepts_what_the_validator_accepts():
    jsonschema = pytest.importorskip("jsonschema")
    schema = byo.verdict_schema(RULES)
    good = client_verdicts(ACCEPTED)
    jsonschema.validate(good, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(good[:-1], schema)


# --- 3. forged and malformed answers get no score -------------------------------------


def _agg(client, verdicts, brief=ACCEPTED, version=None):
    version = version or client.get("/v1/byo/rules").json()["ruleset_version"]
    r = client.post(
        "/v1/byo/aggregate", json={"brief": brief, "verdicts": verdicts, "ruleset_version": version}
    )
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _codes(out):
    return {e["code"] for e in out["errors"] + out["evidence_errors"]}


@pytest.mark.parametrize(
    "mutate, code",
    [
        (lambda vs: vs[:-1], "missing_rule"),
        (lambda vs: vs + [dict(vs[0])], "duplicate_rule"),
        (lambda vs: vs + [{**vs[0], "rule_id": "made-up"}], "unknown_rule"),
        (lambda vs: [{**vs[0], "status": "excellent"}, *vs[1:]], "invalid_status"),
        (lambda vs: [{**vs[0], "confidence": 1.5}, *vs[1:]], "invalid_confidence"),
        (lambda vs: [{**vs[0], "confidence": True}, *vs[1:]], "invalid_confidence"),
        (lambda vs: [{**vs[0], "quote": 42}, *vs[1:]], "non_text_evidence"),
        (lambda vs: [{**vs[0], "score": 100}, *vs[1:]], "unexpected_field"),
        (lambda vs: [{**vs[0], "weight": 99}, *vs[1:]], "unexpected_field"),
        (lambda vs: ["pass", *vs[1:]], "not_an_object"),
        (
            lambda vs: [{**vs[0], "status": "pass", "quote": "a sentence the brief never said"}, *vs[1:]],
            "quote_not_verbatim",
        ),
    ],
)
def test_a_forged_or_broken_answer_gets_no_score(client, mutate, code):
    out = _agg(client, mutate(client_verdicts(ACCEPTED)))
    assert out["valid"] is False and out["result"] is None
    assert code in _codes(out), out


def test_a_stale_ruleset_version_is_refused(client):
    out = _agg(client, client_verdicts(ACCEPTED), version="0.0.1+deadbeef")
    assert out["result"] is None and "ruleset_version_mismatch" in _codes(out)


def test_every_problem_is_reported_at_once(client):
    vs = client_verdicts(ACCEPTED)
    vs[0]["status"] = "great"
    vs[1]["confidence"] = 7
    out = _agg(client, vs[:-1])
    assert {"invalid_status", "invalid_confidence", "missing_rule"} <= _codes(out)


def test_not_an_array_is_refused():
    out = service.aggregate_payload(ACCEPTED, {"all": "pass"}, scorer.version())
    assert out["result"] is None and "not_an_array" in _codes(out)


def test_verbatim_quotes_are_accepted_even_reformatted(client):
    vs = verbatim_verdicts(ACCEPTED)
    vs[0]["quote"] = vs[0]["quote"].upper()  # case is forgiven, words are not
    out = _agg(client, vs)
    assert out["valid"], out["evidence_errors"]


def test_a_contradiction_a_pattern_can_see_is_flagged(client):
    brief = ACCEPTED + "\nWrite to mara@acme.it for access."
    vs = verbatim_verdicts(brief)
    out = _agg(client, vs, brief=brief)
    assert out["valid"]
    assert [c["code"] for c in out["conflicts"]] == ["anonymised_but_contacts"]
    assert out["result"]["review_required"] is True


# --- 4. advisory, never authority ---------------------------------------------------------


def test_every_aggregate_answer_is_tagged_advisory_and_links_the_directory(client):
    for out in (_agg(client, client_verdicts(ACCEPTED)), _agg(client, [])):
        assert out["evaluation_source"] == "client"
        assert out["authoritative"] is False and out["advisory"] is True
        assert out["publication_authority"] == "none"
        assert out["ruleset_version"] == scorer.version()
        assert out["directory"]["label"] == "Find a team on welance/directory →"
        assert out["directory"]["url"].startswith("https://")
        assert "cannot authorise publication" in out["notice"]
    good = _agg(client, client_verdicts(ACCEPTED))
    assert "advisory" in good["result"]["decision_label"]
    assert not {"token", "signature", "grant", "publish_token"} & set(good)


def test_the_authoritative_score_cannot_be_fed_verdicts(client):
    """A forged all-pass answer sent to /v1/score changes nothing: it judges for itself."""
    weak = yaml.safe_load(open(os.path.join(loader.fixtures_dir(), "0001-weak.yaml")))["input"]
    plain = client.post("/v1/score", json={"brief": weak, "judge": "mock"}).json()
    forged = client.post(
        "/v1/score",
        json={
            "brief": weak,
            "judge": "mock",
            "verdicts": verbatim_verdicts(weak),
            "evaluation_source": "server",
            "score": 100,
        },
    ).json()
    assert forged["score"] == plain["score"] and forged["decision"] == plain["decision"]
    assert forged["decision"] != "accepted"


# --- check_brief and the templates ----------------------------------------------------------


def test_check_brief_is_honest_about_what_it_cannot_see(client):
    out = client.post("/v1/byo/check", json={"brief": ACCEPTED + "\nCall +39 347 123 4567."}).json()
    assert out["semantic_coverage"] == "incomplete" and out["score"] is None
    assert "INCOMPLETE" in out["notice"]
    by = {c["id"]: c for c in out["checks"]}
    assert by["contact-details"]["outcome"] == "flag"
    assert by["budget-stated"]["outcome"] == "found"
    assert out["rules_needing_a_model"], "some rules always need a model"
    generic = client.post("/v1/byo/check", json={"brief": ACCEPTED, "directory_context": False}).json()
    assert "anonymised" not in generic["rules_with_a_deterministic_signal"]


def test_check_brief_flags_placeholders(client):
    out = client.post("/v1/byo/check", json={"brief": "# Title\nBudget: [AMOUNT]\nProblem: TBD"}).json()
    by = {c["id"]: c for c in out["checks"]}
    assert by["placeholders"]["outcome"] == "flag"


def test_the_template_follows_the_live_catalogue(client):
    out = client.get("/v1/byo/template").json()
    assert {i["rule_id"] for i in out["required_inputs"]} == set(scorer.rules())
    assert out["template"].startswith("# ")
    rules = client.get("/v1/byo/rules").json()
    assert rules["rule_count"] == len(rules["rules"]) == len(scorer.rules())
    assert "directory" in rules["gate_contexts"]["available"]


def test_the_improvement_prompt_targets_the_gate_first(client):
    weak = yaml.safe_load(open(os.path.join(loader.fixtures_dir(), "0004-blocked-brand.yaml")))["input"]
    out = client.post(
        "/v1/byo/improvement-prompt", json={"brief": weak, "verdicts": client_verdicts(weak)}
    ).json()
    assert out["verdicts_used"] is True
    text = out["prompt"]
    assert "never invent" in text.lower() and weak.strip()[:20] in text
    assert "advisory" in text


def test_byo_inputs_are_bounded(client):
    assert client.post("/v1/byo/check", json={"brief": "  "}).status_code == 422
    too_many = [{"rule_id": "x"}] * 201
    r = client.post("/v1/byo/aggregate", json={"brief": "x", "verdicts": too_many, "ruleset_version": "v"})
    assert r.status_code == 422
