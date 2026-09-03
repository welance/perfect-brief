"""The hosted MCP connector at /mcp.

A chat in the browser cannot call the API, but it can add a remote MCP server.
This is that server, inside the same app. Two promises: it speaks the protocol
over plain JSON POSTs (no session, no event stream), and it is the same bar as
the local stdio server — same tools, same words, same prompt.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-server"))

from app import mcp_http  # noqa: E402

HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream",
    "mcp-protocol-version": "2025-06-18",
}


def payload(result):
    """A tool's answer travels as JSON text, exactly as the stdio server's does."""
    assert not result.get("isError"), result
    return json.loads(result["content"][0]["text"])


def rpc(client, method, params=None, id_=1):
    body = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        body["params"] = params
    r = client.post("/mcp/", json=body, headers=HEADERS)
    assert r.status_code == 200, (method, r.status_code, r.text[:300])
    return r.json()


def test_a_browser_chat_can_initialise_without_a_session(client):
    out = rpc(
        client,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    )
    assert out["result"]["serverInfo"]["name"] == "brief-bar"
    assert "never state a score" in out["result"]["instructions"]


def test_the_four_tools_are_listed(client):
    out = rpc(client, "tools/list")
    assert {t["name"] for t in out["result"]["tools"]} == {
        "get_rules",
        "score_brief",
        "suggest_fixes",
        "bar_status",
    }


def test_scoring_through_the_connector_is_the_api_score(client):
    brief = "# Booking tool\nProblem: staff cannot update availability. Budget 30k. Ship by spring."
    via_api = client.post("/v1/score", json={"brief": brief, "judge": "mock"}).json()
    out = rpc(client, "tools/call", {"name": "score_brief", "arguments": {"brief": brief, "judge": "mock"}})
    got = payload(out["result"])
    assert got["score"] == via_api["score"]
    assert got["decision"] == via_api["decision"]
    assert got["ruleset_version"] == via_api["ruleset_version"]


def test_the_rules_and_the_status_come_through(client):
    rules = payload(rpc(client, "tools/call", {"name": "get_rules", "arguments": {}})["result"])
    assert len(rules["rules"]) == 14
    status = payload(rpc(client, "tools/call", {"name": "bar_status", "arguments": {}})["result"])
    assert status["ruleset_version"] == rules["ruleset_version"]


def test_a_refusal_is_a_readable_error_not_a_crash(client):
    out = rpc(client, "tools/call", {"name": "score_brief", "arguments": {"brief": "", "judge": "mock"}})
    assert out["result"]["isError"] is True
    assert "422" in out["result"]["content"][0]["text"]


# --- one bar, two doors: the hosted server must not drift from the local one --


def test_hosted_and_local_servers_are_the_same_bar():
    local = pytest.importorskip("server", reason="MCP SDK not installed")
    hosted_tools = {t.name: t for t in asyncio.run(mcp_http.server.list_tools())}
    local_tools = {t.name: t for t in asyncio.run(local.server.list_tools())}
    assert hosted_tools.keys() == local_tools.keys()
    for name, tool in local_tools.items():
        assert hosted_tools[name].description == tool.description, name
        schema = lambda t: t.model_dump(by_alias=True)["inputSchema"]["properties"].keys()  # noqa: E731
        assert schema(hosted_tools[name]) == schema(tool), name
    assert mcp_http.improve_brief("X") == local.improve_brief("X")
    assert mcp_http.server.instructions == local.server.instructions
