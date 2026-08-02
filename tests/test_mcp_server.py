"""The MCP server's promises.

The server is thin on purpose — it forwards to the public API — so what is
worth testing is exactly what it decides on its own: which tools exist, what
each one sends, that a caller's key is forwarded and never mangled, and that
the prompt keeps telling assistants the two things that make the bar useful
(fix the gate first, never invent a score).

Offline: the HTTP layer is stubbed, so these run in CI with no network. The
coroutines are driven with asyncio.run rather than a plugin — one dependency
fewer for something this small.
"""

from __future__ import annotations

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

server = pytest.importorskip("server", reason="MCP SDK not installed")


@pytest.fixture
def calls(monkeypatch):
    """Capture what the server would send, without sending it."""
    seen: list[tuple[str, str, dict]] = []

    async def fake_post(path, payload):
        seen.append(("POST", path, payload))
        return {"score": 92.0, "decision": "blocked", "gate": {"passed": False, "missing": ["anonymised"]}}

    async def fake_get(path):
        seen.append(("GET", path, {}))
        return {"rules": [], "budget_floor": 10000}

    monkeypatch.setattr(server, "_post", fake_post)
    monkeypatch.setattr(server, "_get", fake_get)
    return seen


# --- the tool surface is part of the promise ------------------------------


def test_the_four_tools_and_the_prompt_exist():
    tools = {t.name for t in asyncio.run(server.server.list_tools())}
    assert tools == {"get_rules", "score_brief", "suggest_fixes", "bar_status"}
    prompts = {p.name for p in asyncio.run(server.server.list_prompts())}
    assert prompts == {"improve_brief"}


def test_every_tool_explains_itself():
    """An assistant reads these descriptions to decide what to call."""
    for tool in asyncio.run(server.server.list_tools()):
        assert tool.description and len(tool.description) > 60, tool.name


# --- what each tool actually sends ----------------------------------------


def test_score_brief_sends_the_brief_and_the_configured_judge(calls):
    asyncio.run(server.score_brief("a brief"))
    method, path, payload = calls[0]
    assert (method, path) == ("POST", "/v1/score")
    assert payload["brief"] == "a brief"
    assert payload["judge"] == server.JUDGE


def test_directory_context_off_drops_the_policy_rules(calls):
    asyncio.run(server.score_brief("a brief", directory_context=False))
    assert calls[0][2]["gate_contexts"] == []
    calls.clear()
    asyncio.run(server.score_brief("a brief", directory_context=True))
    assert "gate_contexts" not in calls[0][2], "default keeps every context active"


def test_suggest_fixes_targets_rules_when_asked(calls):
    asyncio.run(server.suggest_fixes("a brief"))
    assert "rule_ids" not in calls[0][2], "default: every failing rule"
    calls.clear()
    asyncio.run(server.suggest_fixes("a brief", ["timeline"]))
    assert calls[0][2]["rule_ids"] == ["timeline"]


def test_reading_the_bar_is_a_plain_get(calls):
    asyncio.run(server.get_rules())
    asyncio.run(server.bar_status())
    assert [(m, p) for m, p, _ in calls] == [("GET", "/v1/rules"), ("GET", "/v1/healthz")]


# --- bring your own key ----------------------------------------------------


def test_the_key_is_forwarded_verbatim_and_only_when_present(monkeypatch):
    monkeypatch.setattr(server, "LLM_KEY", None)
    assert "x-llm-key" not in server._headers()
    monkeypatch.setattr(server, "LLM_KEY", "sk-or-secret")
    headers = server._headers()
    assert headers["x-llm-key"] == "sk-or-secret"
    assert headers["content-type"] == "application/json"


# --- the prompt is where the discipline lives ------------------------------


def test_the_prompt_keeps_the_two_rules_that_matter():
    text = server.improve_brief("MY BRIEF")
    assert "MY BRIEF" in text
    lowered = text.lower()
    assert "gate.missing" in lowered, "the gate must be fixed before anything else"
    assert "never invent" in lowered, "a score must come from the tool or not at all"
    assert "get_rules" in text and "score_brief" in text
    assert text.index("get_rules") < text.index("score_brief"), "read the bar, then judge"


def test_the_prompt_works_without_a_brief():
    assert "paste the brief here" in server.improve_brief().lower()
