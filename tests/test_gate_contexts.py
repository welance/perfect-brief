"""Directory context: anonymised and budget-floor are welance/Directory
noticeboard policy (blindness, the €10k floor), not properties of a good
generic brief. Both the rules and their gate entries carry `context:
directory` and deactivate together per call — the rules then neither gate
nor score (excluded + renormalised). Verdicts themselves never change.
"""

from perfect_brief import Status, Verdict, aggregate, load_bundled

RULES, CFG = load_bundled()
DIRECTORY_RULES = {"anonymised", "budget-floor"}


def _verdicts(fail: set[str] = frozenset()) -> list[Verdict]:
    return [
        Verdict(rule_id=r.id, status=Status.FAIL if r.id in fail else Status.PASS, confidence=0.9)
        for r in RULES.values()
    ]


def test_directory_policy_is_tagged_in_rules_and_gate():
    for rid in DIRECTORY_RULES:
        assert RULES[rid].context == "directory"
        entry = next(g for g in CFG.gate if g["rule"] == rid)
        assert entry.get("context") == "directory"
    # everything else stays unconditional
    assert all(r.context is None for r in RULES.values() if r.id not in DIRECTORY_RULES)
    assert all("context" not in g for g in CFG.gate if g["rule"] not in DIRECTORY_RULES)


def test_default_keeps_blind_gate():
    res = aggregate(_verdicts(fail={"anonymised"}), RULES, CFG)
    assert res.decision == "blocked"
    assert "anonymised" in res.gate_missing
    assert res.gate_contexts == ["directory"]
    assert res.excluded == []


def test_directory_context_off_removes_rules_and_gates():
    res = aggregate(_verdicts(fail={"anonymised", "budget-floor"}), RULES, CFG, contexts=[])
    assert res.gate_passed
    assert res.gate_missing == []
    assert res.gate_contexts == []
    assert set(res.excluded) == DIRECTORY_RULES
    # excluded rules cost nothing: everything else passes -> renormalised 100
    assert res.score == 100.0
    assert res.decision == "accepted"
    assert not any(c.rule_id in DIRECTORY_RULES for c in res.contributions)


def test_context_off_leaves_unconditional_gates():
    res = aggregate(_verdicts(fail={"problem-defined"}), RULES, CFG, contexts=[])
    assert not res.gate_passed
    assert res.gate_missing == ["problem-defined"]


def test_explicit_directory_context_matches_default():
    default = aggregate(_verdicts(fail={"anonymised"}), RULES, CFG)
    explicit = aggregate(_verdicts(fail={"anonymised"}), RULES, CFG, contexts=["directory"])
    assert (default.decision, default.gate_missing, default.score) == (
        explicit.decision,
        explicit.gate_missing,
        explicit.score,
    )
