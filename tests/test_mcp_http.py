"""The remote MCP server at /mcp: free, bring your own model.

A chat in the browser or an editor adds this URL as a connector. Promises:
it speaks the protocol over plain JSON POSTs (no session, no event stream) in
every revision the SDK negotiates, it refuses JSON-RPC batches cleanly, it
never calls a provider, and it is the same bar as the local stdio server —
same tools, same words, same prompts and resources.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from app import llm_client, mcp_http, scorer  # noqa: E402
from brief_bar import load_bundled, loader  # noqa: E402

BYO_TOOLS = {
    "get_rules",
    "get_brief_template",
    "get_judge_prompt",
    "get_improvement_prompt",
    "check_brief",
    "aggregate_verdicts",
    "bar_status",
}
HANDSHAKE_VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"]
MODERN = "2026-07-28"
RULES, _ = load_bundled()
BRIEF = yaml.safe_load(open(os.path.join(loader.fixtures_dir(), "0003-accepted.yaml")))["input"]


def headers(version: str | None = "2025-06-18", **extra) -> dict:
    h = {"content-type": "application/json", "accept": "application/json, text/event-stream"}
    if version:
        h["mcp-protocol-version"] = version
    h.update(extra)
    return h


def payload(result):
    """A tool's answer travels as JSON text."""
    assert not result.get("isError"), result
    return json.loads(result["content"][0]["text"])


def rpc(client, method, params=None, id_=1, version="2025-06-18"):
    body = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        body["params"] = params
    r = client.post("/mcp/", json=body, headers=headers(version))
    assert r.status_code == 200, (method, r.status_code, r.text[:300])
    return r.json()


def call(client, name, **arguments):
    return payload(rpc(client, "tools/call", {"name": name, "arguments": arguments})["result"])


def init(version):
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": version,
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    }


def test_the_documented_url_without_a_trailing_slash_answers(client):
    r = client.post("/mcp", json=init("2025-06-18"), headers=headers(None))
    assert r.status_code == 200, r.text[:300]
    assert r.json()["result"]["serverInfo"]["name"] == "perfect-brief"


# --- protocol: negotiation, batching, both eras ----------------------------------------


@pytest.mark.parametrize("version", HANDSHAKE_VERSIONS)
def test_every_handshake_revision_is_accepted_without_a_session(client, version):
    r = client.post("/mcp/", json=init(version), headers=headers(None))
    assert r.status_code == 200
    out = r.json()["result"]
    assert out["protocolVersion"] == version
    assert out["serverInfo"]["name"] == "perfect-brief"
    assert "aggregate_verdicts" in out["instructions"]
    assert "mcp-session-id" not in {k.lower() for k in r.headers}


def test_an_unknown_revision_gets_the_latest_handshake_counter_offer(client):
    r = client.post("/mcp/", json=init("1999-01-01"), headers=headers(None))
    assert r.json()["result"]["protocolVersion"] == HANDSHAKE_VERSIONS[-1]


def test_a_json_rpc_batch_is_refused_cleanly(client):
    batch = [{"jsonrpc": "2.0", "id": i, "method": "tools/list"} for i in (1, 2)]
    r = client.post("/mcp/", json=batch, headers=headers())
    assert r.status_code == 400
    assert r.json()["error"]["code"] in (-32600, -32602)


def test_the_stateless_2026_envelope_works(client):
    meta = {
        "io.modelcontextprotocol/protocolVersion": MODERN,
        "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }

    def modern(method, params=None, **extra):
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": {**(params or {}), "_meta": meta}}
        r = client.post("/mcp/", json=body, headers=headers(MODERN, **{"mcp-method": method, **extra}))
        assert r.status_code == 200, r.text[:300]
        return r.json()["result"]

    assert "tools" in modern("server/discover")["capabilities"]
    assert {t["name"] for t in modern("tools/list")["tools"]} == BYO_TOOLS
    status = modern("tools/call", {"name": "bar_status", "arguments": {}}, **{"mcp-name": "bar_status"})
    assert json.loads(status["content"][0]["text"])["provider_calls"] == 0


def test_a_malformed_modern_request_is_a_structured_refusal(client):
    r = client.post(
        "/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers=headers("2099-01-01")
    )
    assert r.status_code == 400 and "error" in r.json()


# --- the surface ----------------------------------------------------------------------------


def test_the_seven_tools_are_listed_and_read_only(client):
    tools = rpc(client, "tools/list")["result"]["tools"]
    assert {t["name"] for t in tools} == BYO_TOOLS
    for t in tools:
        assert t["annotations"]["readOnlyHint"] is True, t["name"]
        assert t["annotations"]["openWorldHint"] is False, t["name"]


def test_prompts_and_resources_mirror_the_tools(client):
    prompts = {p["name"] for p in rpc(client, "prompts/list")["result"]["prompts"]}
    assert prompts == {"judge_brief", "improve_brief", "brief_template"}
    uris = {r["uri"] for r in rpc(client, "resources/list")["result"]["resources"]}
    assert uris == {
        "perfect-brief://rules",
        "perfect-brief://template",
        "perfect-brief://judge-prompt",
        "perfect-brief://verdict-schema",
    }
    schema = rpc(client, "resources/read", {"uri": "perfect-brief://verdict-schema"})["result"]
    assert json.loads(schema["contents"][0]["text"])["maxItems"] == len(RULES)
    got = rpc(client, "prompts/get", {"name": "judge_brief", "arguments": {"brief": "MY BRIEF"}})["result"]
    assert "MY BRIEF" in got["messages"][0]["content"]["text"]


def test_the_whole_byo_loop_through_the_connector(client):
    rules = call(client, "get_rules")
    assert rules["rule_count"] == len(RULES)
    prompt = call(client, "get_judge_prompt", brief=BRIEF)
    verdicts = [
        {"rule_id": rid, "status": "pass", "confidence": 0.9, "quote": "", "note": ""}
        for rid in prompt["rule_ids"]
    ]
    out = call(
        client,
        "aggregate_verdicts",
        brief=BRIEF,
        verdicts=verdicts,
        ruleset_version=prompt["ruleset_version"],
    )
    assert out["valid"] and out["result"]["score"] == 100.0
    assert out["evaluation_source"] == "client" and out["authoritative"] is False
    assert out["directory"]["label"].startswith("Find a team on welance/directory")
    # a model handing over its raw JSON text, fenced, is understood too
    fenced = "```json\n" + json.dumps(verdicts) + "\n```"
    again = call(
        client, "aggregate_verdicts", brief=BRIEF, verdicts=fenced, ruleset_version=rules["ruleset_version"]
    )
    assert again["result"] == out["result"]
    check = call(client, "check_brief", brief=BRIEF)
    assert check["semantic_coverage"] == "incomplete"
    assert call(client, "get_improvement_prompt", brief=BRIEF, verdicts=verdicts)["verdicts_used"] is True
    assert call(client, "get_brief_template")["template"].startswith("# ")


def test_the_connector_makes_no_provider_call(client, monkeypatch):
    calls = []

    async def complete(*a, **k):
        calls.append(1)
        raise AssertionError("provider called")

    monkeypatch.setattr(llm_client, "complete", complete)
    monkeypatch.setattr(llm_client, "configured", lambda: True)
    for name, args in [
        ("get_rules", {}),
        ("get_brief_template", {}),
        ("get_judge_prompt", {"brief": BRIEF}),
        ("get_improvement_prompt", {"brief": BRIEF}),
        ("check_brief", {"brief": BRIEF}),
        ("aggregate_verdicts", {"brief": BRIEF, "verdicts": [], "ruleset_version": scorer.version()}),
        ("bar_status", {}),
    ]:
        call(client, name, **args)
    for p in ("judge_brief", "improve_brief", "brief_template"):
        rpc(client, "prompts/get", {"name": p, "arguments": {}})
    assert calls == []


def test_no_tool_scores_with_the_service_judge(client):
    names = {t["name"] for t in rpc(client, "tools/list")["result"]["tools"]}
    assert not {"score_brief", "suggest_fixes"} & names


def test_a_refusal_is_a_readable_error_not_a_crash(client):
    out = rpc(client, "tools/call", {"name": "check_brief", "arguments": {"brief": "  "}})
    assert out["result"]["isError"] is True
    assert "422" in out["result"]["content"][0]["text"]
    bad = rpc(
        client,
        "tools/call",
        {
            "name": "aggregate_verdicts",
            "arguments": {"brief": BRIEF, "verdicts": "{not json", "ruleset_version": "x"},
        },
    )
    assert bad["result"]["isError"] is True


# --- the service-judge connector is separate and off by default ---------------------------


def test_the_hosted_connector_is_not_served_by_default(client):
    r = client.post("/mcp-hosted/", json=init("2025-06-18"), headers=headers(None))
    assert r.status_code != 200


def test_the_hosted_connector_keeps_its_scoring_tools():
    names = {t.name for t in asyncio.run(mcp_http.hosted.list_tools())}
    assert {"score_brief", "suggest_fixes", "get_rules", "bar_status"} == names


# --- one bar, two doors: the remote server must not drift from the local one ---------------


def test_remote_and_local_servers_are_the_same_bar():
    local = pytest.importorskip("server", reason="MCP SDK not installed")
    remote_tools = {t.name: t for t in asyncio.run(mcp_http.server.list_tools())}
    local_tools = {t.name: t for t in asyncio.run(local.server.list_tools())}
    assert remote_tools.keys() == local_tools.keys() == BYO_TOOLS
    for name, tool in local_tools.items():
        assert remote_tools[name].description == tool.description, name

        def schema(t):
            return t.model_dump(by_alias=True)["inputSchema"]["properties"]

        assert schema(remote_tools[name]) == schema(tool), name
        assert remote_tools[name].annotations == tool.annotations, name
        assert remote_tools[name].title == tool.title, name
    remote_prompts = {p.name: (p.title, p.description) for p in asyncio.run(mcp_http.server.list_prompts())}
    local_prompts = {p.name: (p.title, p.description) for p in asyncio.run(local.server.list_prompts())}
    assert remote_prompts == local_prompts
    remote_res = {str(r.uri): (r.title, r.description) for r in asyncio.run(mcp_http.server.list_resources())}
    local_res = {str(r.uri): (r.title, r.description) for r in asyncio.run(local.server.list_resources())}
    assert remote_res == local_res
    assert mcp_http.server.instructions == local.server.instructions


# --- directory listings: Claude's and ChatGPT's reviews read these fields ---------------------


def _all_tool_sets():
    """Every tool any of our MCP servers can list, remote and local, default and opt-in."""
    local = pytest.importorskip("server", reason="MCP SDK not installed")
    from mcp.server.mcpserver import MCPServer

    opt_in = MCPServer("opt-in")
    local.register_hosted_tools(opt_in)
    return {
        "remote": asyncio.run(mcp_http.server.list_tools()),
        "remote-hosted": asyncio.run(mcp_http.hosted.list_tools()),
        "local": asyncio.run(local.server.list_tools()),
        "local-opt-in": asyncio.run(opt_in.list_tools()),
    }


def test_every_tool_has_a_title_and_explicit_safety_hints():
    for where, tools in _all_tool_sets().items():
        assert tools, where
        for t in tools:
            assert t.title and t.title.strip(), (where, t.name)
            assert t.annotations is not None, (where, t.name)
            hints = t.annotations
            # the directories require readOnlyHint or destructiveHint; we state all four
            assert hints.read_only_hint is not None or hints.destructive_hint is not None, (where, t.name)
            for field in ("read_only_hint", "destructive_hint", "idempotent_hint", "open_world_hint"):
                assert getattr(hints, field) is not None, (where, t.name, field)
            # nothing any of our servers exposes writes or deletes anything
            assert hints.read_only_hint is True and hints.destructive_hint is False, (where, t.name)


def test_only_the_service_judge_tools_reach_a_model_provider():
    for where, tools in _all_tool_sets().items():
        for t in tools:
            expected = t.name in {"score_brief", "suggest_fixes"}
            assert t.annotations.open_world_hint is expected, (where, t.name)


def test_the_opt_in_tools_match_the_remote_hosted_ones():
    sets = _all_tool_sets()
    remote = {t.name: (t.title, t.annotations) for t in sets["remote-hosted"]}
    for t in sets["local-opt-in"]:
        assert remote[t.name] == (t.title, t.annotations), t.name


def test_the_listing_metadata_travels_over_the_wire(client):
    tools = rpc(client, "tools/list")["result"]["tools"]
    for t in tools:
        assert t["title"], t["name"]
        assert {"readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"} <= t[
            "annotations"
        ].keys()
    assert all(p.get("title") for p in rpc(client, "prompts/list")["result"]["prompts"])
    assert all(r.get("title") for r in rpc(client, "resources/list")["result"]["resources"])
    info = client.post("/mcp/", json=init("2025-06-18"), headers=headers(None)).json()["result"]
    assert info["serverInfo"]["title"] == "brief bar"
    assert info["serverInfo"]["websiteUrl"] == "https://briefs.welance.com"
    assert "https://briefs.welance.com/privacy.html" in info["instructions"]
    assert "https://briefs.welance.com/terms.html" in info["instructions"]
