"""Gate contexts: a gate requirement tagged with `context:` is instrumental
to a specific consumer (anonymised -> the Directory's blind noticeboard) and
can be deactivated per call. Deactivation only relaxes the gate — the rule
still scores, and the verdict is unchanged.
"""

from perfect_brief import Status, Verdict, aggregate, load_bundled

RULES, CFG = load_bundled()


def _verdicts(anonymised: Status = Status.PASS) -> list[Verdict]:
    """Every rule passes except (optionally) anonymised."""
    return [
        Verdict(rule_id=r.id, status=anonymised if r.id == "anonymised" else Status.PASS, confidence=0.9)
        for r in RULES.values()
    ]


def test_anonymised_gate_entry_is_directory_context():
    entry = next(g for g in CFG.gate if g["rule"] == "anonymised")
    assert entry.get("context") == "directory"
    # the other requirements stay unconditional
    assert all("context" not in g for g in CFG.gate if g["rule"] != "anonymised")


def test_default_keeps_blind_gate():
    res = aggregate(_verdicts(Status.FAIL), RULES, CFG)
    assert res.decision == "blocked"
    assert "anonymised" in res.gate_missing
    assert res.gate_contexts == ["directory"]


def test_directory_context_off_unblocks():
    res = aggregate(_verdicts(Status.FAIL), RULES, CFG, contexts=[])
    assert res.gate_passed
    assert res.gate_missing == []
    assert res.gate_contexts == []
    # the rule still scores: a leaked brand still costs its 8 points
    assert res.score is not None and res.score < 100.0
    assert res.decision in ("accepted", "reserved")


def test_context_off_leaves_unconditional_gates():
    verdicts = [
        Verdict(
            rule_id=r.id,
            status=Status.FAIL if r.id == "problem-defined" else Status.PASS,
            confidence=0.9,
        )
        for r in RULES.values()
    ]
    res = aggregate(verdicts, RULES, CFG, contexts=[])
    assert not res.gate_passed
    assert res.gate_missing == ["problem-defined"]


def test_explicit_directory_context_matches_default():
    default = aggregate(_verdicts(Status.FAIL), RULES, CFG)
    explicit = aggregate(_verdicts(Status.FAIL), RULES, CFG, contexts=["directory"])
    assert (default.decision, default.gate_missing) == (explicit.decision, explicit.gate_missing)
