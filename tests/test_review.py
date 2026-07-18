"""Verifier primitives: prompt rendering and verdict parsing (no network)."""

from perfect_brief import llm


def test_render_review_prompt_contains_items_and_criteria():
    items = [{"id": "budget-floor", "requirement": "state a budget", "text": "Budget is 8000 EUR."}]
    p = llm.render_review_prompt(items, "We need a landing page. Budget 8000 EUR.")
    assert "budget-floor" in p
    assert "Budget is 8000 EUR." in p
    for criterion in ("ANCHORED", "ON-RULE", "ACTIONABLE"):
        assert criterion in p


def test_parse_review_roundtrip():
    raw = '[{"id":"budget-floor","accepted":true,"reason":"cites the 8000 EUR figure"}]'
    out = llm.parse_review(raw)
    assert out == {"budget-floor": {"accepted": True, "reason": "cites the 8000 EUR figure"}}


def test_parse_review_tolerates_fences_and_junk():
    raw = '```json\n[{"id":"a","accepted":false,"reason":"generic"},{"nonsense":1}]\n```'
    out = llm.parse_review(raw)
    assert out == {"a": {"accepted": False, "reason": "generic"}}


def test_suggest_prompts_carry_critiques():
    from perfect_brief import load_bundled

    rules, _ = load_bundled()
    rule = rules["budget-floor"]
    p1 = llm.render_suggest_prompt(rule, "brief text", critique="too generic, name the currency")
    assert "too generic, name the currency" in p1
    p2 = llm.render_suggest_all_prompt([rule], "brief text", critiques={"budget-floor": "cite the real figure"})
    assert "cite the real figure" in p2
