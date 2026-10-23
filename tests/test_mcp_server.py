"""The stdio MCP server's promises.

The server is thin on purpose — it forwards to the public API's free
`/v1/byo/*` routes — so what is worth testing is what it decides on its own:
which tools exist, what each one sends, that the free tools never carry a
provider key, and that the legacy service-judge tools appear only on request.

Offline: the HTTP layer is stubbed. A last test drives the real stdio server
against the real app in-process, so the two halves are known to fit.
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

server = pytest.importorskip("server", reason="MCP SDK not installed")

BYO_TOOLS = {
    "get_rules",
    "get_brief_template",
    "get_judge_prompt",
    "get_improvement_prompt",
    "check_brief",
    "aggregate_verdicts",
    "bar_status",
}


@pytest.fixture
def calls(monkeypatch):
    """Capture what the server would send, without sending it."""
    seen: list[tuple[str, str, dict, bool]] = []

    async def fake_post(path, payload, byok=False):
        seen.append(("POST", path, payload, byok))
        return {"prompt": "P", "verdict_schema": {}, "template": "T"}

    async def fake_get(path):
        seen.append(("GET", path, {}, False))
        return {"template": "T"}

    monkeypatch.setattr(server, "_post", fake_post)
    monkeypatch.setattr(server, "_get", fake_get)
    return seen


def test_the_free_tools_prompts_and_resources_exist():
    assert {t.name for t in asyncio.run(server.server.list_tools())} == BYO_TOOLS
    assert {p.name for p in asyncio.run(server.server.list_prompts())} == {
        "judge_brief",
        "improve_brief",
        "brief_template",
    }
    assert len(asyncio.run(server.server.list_resources())) == 4


def test_every_tool_explains_itself():
    for tool in asyncio.run(server.server.list_tools()):
        assert tool.description and len(tool.description) > 60, tool.name


def test_each_tool_calls_its_free_route(calls):
    asyncio.run(server.get_rules())
    asyncio.run(server.get_brief_template())
    asyncio.run(server.get_judge_prompt("a brief"))
    asyncio.run(server.get_improvement_prompt("a brief", '[{"rule_id": "timeline"}]'))
    asyncio.run(server.check_brief("a brief", directory_context=False))
    asyncio.run(server.aggregate_verdicts("a brief", [{"rule_id": "x"}], "1.0.0+abc"))
    asyncio.run(server.bar_status())
    assert [(m, p) for m, p, _, _ in calls] == [
        ("GET", "/v1/byo/rules"),
        ("GET", "/v1/byo/template"),
        ("POST", "/v1/byo/judge-prompt"),
        ("POST", "/v1/byo/improvement-prompt"),
        ("POST", "/v1/byo/check"),
        ("POST", "/v1/byo/aggregate"),
        ("GET", "/v1/byo/status"),
    ]
    assert calls[3][2]["verdicts"] == [{"rule_id": "timeline"}], "JSON text is parsed"
    assert calls[4][2]["directory_context"] is False
    assert calls[5][2]["ruleset_version"] == "1.0.0+abc"
    assert not any(byok for *_, byok in calls), "the free tools never carry a key"


def test_no_key_travels_on_the_free_tools(monkeypatch):
    monkeypatch.setattr(server, "LLM_KEY", "sk-or-secret")
    assert "x-llm-key" not in server._headers()
    assert server._headers(byok=True)["x-llm-key"] == "sk-or-secret"


def test_the_service_judge_tools_are_opt_in(calls):
    assert not {"score_brief", "suggest_fixes"} & {t.name for t in asyncio.run(server.server.list_tools())}
    from mcp.server.mcpserver import MCPServer

    legacy = MCPServer("legacy")
    server.register_hosted_tools(legacy)
    assert {t.name for t in asyncio.run(legacy.list_tools())} == {"score_brief", "suggest_fixes"}
    asyncio.run(server.score_brief("a brief", directory_context=False))
    method, path, body, byok = calls[0]
    assert (path, body["gate_contexts"], byok) == ("/v1/score", [], True)


def test_the_stdio_server_fits_the_real_api(client, monkeypatch):
    """The adapter's requests, answered by the app itself: the two halves fit."""

    async def post(path, payload, byok=False):
        r = client.post(path, json=payload)
        assert r.status_code == 200, (path, r.text[:300])
        return r.json()

    async def get(path):
        return client.get(path).json()

    monkeypatch.setattr(server, "_post", post)
    monkeypatch.setattr(server, "_get", get)
    prompt = asyncio.run(server.get_judge_prompt("Title: X\nProblem: Y"))
    verdicts = [
        {"rule_id": r, "status": "fail", "confidence": 0.8, "quote": "", "note": ""}
        for r in prompt["rule_ids"]
    ]
    out = asyncio.run(server.aggregate_verdicts("Title: X\nProblem: Y", verdicts, prompt["ruleset_version"]))
    assert out["valid"] and out["result"]["decision"] == "blocked"
    assert "paste the brief here" in asyncio.run(server.improve_brief()).lower()
    assert asyncio.run(server.brief_template()).startswith("# ")


def test_http_errors_are_readable(monkeypatch):
    def handler(request):
        return httpx.Response(422, json={"detail": "brief is empty"})

    real = httpx.AsyncClient
    monkeypatch.setattr(
        server.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )
    with pytest.raises(RuntimeError, match="422"):
        asyncio.run(server.check_brief(""))
