"""Endpoint tests on the mock judge — deterministic, no network."""


def test_healthz(client):
    r = client.get("/v1/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["ruleset_version"].startswith("1.0.0+")
    assert body["llm_configured"] is False


def test_rules_catalogue(client):
    r = client.get("/v1/rules")
    assert r.status_code == 200
    body = r.json()
    assert len(body["rules"]) == 14
    assert body["budget_floor"] == 10000
    gate_rules = {g["rule"] for g in body["gate"]}
    assert gate_rules == {"clear-title", "problem-defined", "budget-floor", "anonymised"}


def test_score_accepted(client):
    brief = (
        "# Real-time availability for restaurant bookings\n\n"
        "Problem: small restaurants lose bookings because staff can't update availability in real time. "
        "Primary users: shift managers at independent restaurants on mobile during service. "
        "Success: reduce no-show bookings by 30% within two seasons. "
        "Deliverables: an auth login with sessions in Postgres and an availability API endpoint with p95 under 200ms. "
        "Out of scope: native apps in v1. Budget band 25-40k. Ship before the spring season. "
        "Needs a full-stack developer and a designer for eight weeks. "
        "Built on the existing Next.js and Postgres stack; integrates with the existing payment provider. "
        "Risk: restaurants may not keep availability current, so we validate that first. "
        "Stores customer booking history; GDPR lawful basis is contract; a DPA is required. "
        "The public booking page targets WCAG 2.2 AA."
    )
    r = client.post("/v1/score", json={"brief": brief, "judge": "mock"})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "accepted"
    assert body["gate"]["passed"] is True
    assert body["score"] >= 85
    assert body["ruleset_version"].startswith("1.0.0+")


def test_high_score_but_gate_blocked(client):
    """The load-bearing demo: quality is not admissibility."""
    brief = (
        "# Real-time availability for restaurant bookings\n\n"
        "Problem: restaurants lose bookings because staff can't update availability. "
        "Primary users: shift managers. Success: reduce no-shows by 30% within two seasons. "
        "Deliverables: an auth login with sessions and an availability API endpoint. Out of scope: native apps. "
        "Budget band 25-40k. Ship before the spring season. Needs a full-stack developer and a designer. "
        "Integrates with our Stripe account; contact mara.rossi@acme.it. "
        "Risk: low adoption, we validate first. Stores customer booking history; GDPR lawful basis is contract. "
        "The public booking page targets WCAG 2.2 AA."
    )
    r = client.post("/v1/score", json={"brief": brief, "judge": "mock"})
    assert r.status_code == 200
    body = r.json()
    assert body["score"] >= 85  # high quality
    assert body["decision"] == "blocked"  # but blocked
    assert "anonymised" in body["gate"]["missing"]
    assert body["gate"]["contexts"] == ["directory"]


def test_gate_contexts_off_scores_generic_brief(client):
    """Same brand-leaking brief, but scored outside the Directory context:
    anonymised no longer gates (it still costs its score points)."""
    brief = (
        "# Real-time availability for restaurant bookings\n\n"
        "Problem: restaurants lose bookings because staff can't update availability. "
        "Primary users: shift managers. Success: reduce no-shows by 30% within two seasons. "
        "Deliverables: an auth login with sessions and an availability API endpoint. Out of scope: native apps. "
        "Budget band 25-40k. Ship before the spring season. Needs a full-stack developer and a designer. "
        "Integrates with our Stripe account; contact mara.rossi@acme.it. "
        "Risk: low adoption, we validate first. Stores customer booking history; GDPR lawful basis is contract. "
        "The public booking page targets WCAG 2.2 AA."
    )
    r = client.post("/v1/score", json={"brief": brief, "judge": "mock", "gate_contexts": []})
    assert r.status_code == 200
    body = r.json()
    assert body["gate"]["passed"] is True
    assert body["gate"]["contexts"] == []
    assert body["decision"] in ("accepted", "reserved")
    anon = next(v for v in body["verdicts"] if v["rule_id"] == "anonymised")
    assert anon["status"] == "fail"  # the verdict itself is unchanged


def test_empty_brief_422(client):
    r = client.post("/v1/score", json={"brief": "   ", "judge": "mock"})
    assert r.status_code == 422


def test_llm_judge_unconfigured_503(client):
    r = client.post("/v1/score", json={"brief": "anything", "judge": "llm"})
    assert r.status_code == 503


def test_suggest_requires_llm_503(client):
    r = client.post("/v1/suggest", json={"brief": "x", "rule_id": "budget-floor"})
    assert r.status_code == 503
