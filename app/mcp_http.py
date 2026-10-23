"""Perfect Brief as a remote MCP server: `POST /mcp` (free, bring your own model).

A chat in the browser (claude.ai, ChatGPT) or an editor (Cursor, VS Code)
adds this URL as a connector; the platform makes the calls. Nothing here runs
a model. The client's own model judges the brief with the service judge's own
prompt; the tools here hand out the bar and do the arithmetic, with the very
engine `/v1/score` uses. Results are tagged `evaluation_source: "client"` and
are advisory: they can never authorise publication on the welance/directory,
which keeps scoring every brief itself on `/v1/score`.

Design:
- Seven tools, three prompts, four resources, all thin doors onto `app.byo`.
  The stdio adapter in `mcp-server/` exposes the same names and words; a test
  holds the two in parity.
- Zero provider calls: this module never imports the LLM client, takes no
  key, and has no fallback to the service judge. A test holds it to that.
- Stateless, JSON responses: every call is one POST with one JSON reply, no
  session to keep and no event stream for the ingress to time out. Protocol
  negotiation (2024-11-05 … 2025-11-25 via `initialize`, and the stateless
  2026-07-28 envelope) and the refusal of JSON-RPC batches are the SDK's;
  tests pin both.

The previous connector, whose `score_brief` and `suggest_fixes` spend the
service-funded judge, is kept separately as `hosted` at `/mcp-hosted`, off
unless `PB_MCP_HOSTED_ENABLED` is set, and then under the same per-address
limits as the API it calls.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from starlette.requests import Request

from app import byo
from app.models import ScoreRequest, SuggestAllRequest

INSTRUCTIONS = (
    "Perfect Brief: an open bar for digital product briefs, free, with your own model. "
    "Read the rules (get_rules), judge the brief with your own model using get_judge_prompt, then "
    "send your JSON verdicts to aggregate_verdicts: the bar's own code computes score, gate and "
    "decision. Fix the gate first. Never state a score you did not get from aggregate_verdicts, and "
    "say it is client-judged and advisory: only the welance/directory's own scoring can publish."
)

READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)

server = MCPServer("perfect-brief", instructions=INSTRUCTIONS)

# The free per-address limit from app.main, bound after it is defined. Kept
# behind a name so this module never imports main (which imports this one).
_free_limit: Callable[[Request], Awaitable[None]] | None = None


def _request(ctx: Context) -> Request:
    req = ctx.request_context.request
    if req is None:  # pragma: no cover - only over a non-HTTP transport
        raise RuntimeError("the hosted connector runs over HTTP only")
    return req


async def _free(ctx: Context, call: Callable[[], Any]) -> Any:
    """Run a BYO call: the free per-address limit first, API refusals as readable text."""
    assert _free_limit is not None, "app.main must bind() before the first call"
    try:
        await _free_limit(_request(ctx))
        return call()
    except HTTPException as exc:
        raise ToolError(f"{exc.status_code}: {exc.detail}") from exc


def _verdict_list(verdicts: list[dict[str, Any]] | str) -> Any:
    """Models often hand over their answer as the JSON text they wrote. Accept both."""
    if isinstance(verdicts, str):
        text = verdicts.strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ToolError("verdicts is not valid JSON: send the array your model returned") from exc
    return verdicts


# ---- tools ---------------------------------------------------------------------


@server.tool(annotations=READ_ONLY)
async def get_rules(ctx: Context) -> dict:
    """Read the bar before judging anything. Free; no model runs.

    Returns the live catalogue with its version: every rule's id, title,
    criteria (what the judge reads), weight, gate role, policy context and how
    to pass it, plus the arithmetic — status scores, confidence threshold,
    accept threshold, bands, the gate and which policy contexts can be turned
    off. The number of rules is whatever the live catalogue says.
    """
    return await _free(ctx, byo.rules_payload)


@server.tool(annotations=READ_ONLY)
async def get_brief_template(ctx: Context) -> dict:
    """A brief template built from the live rules, with the inputs each section needs.

    Use it to start a brief from nothing, or to see which section a gap belongs
    in. Markdown, one section per rule, gate rules marked; write in any language.
    """
    return await _free(ctx, byo.template_payload)


@server.tool(annotations=READ_ONLY)
async def get_judge_prompt(ctx: Context, brief: str = "") -> dict:
    """The judge prompt and verdict JSON Schema, for YOUR model to answer. Free.

    This is the service judge's own prompt, word for word, so your model grades
    against the same bar. Pass the brief to get it embedded, or leave it empty
    for a template with a {{BRIEF}} placeholder. Answer the prompt with your
    own model (temperature 0 if you can), return only the JSON array it asks
    for, and send that array with the brief and the returned ruleset_version to
    aggregate_verdicts. welance runs no model for this.
    """
    return await _free(ctx, lambda: byo.judge_prompt_payload(brief or None))


@server.tool(annotations=READ_ONLY)
async def get_improvement_prompt(
    ctx: Context,
    brief: str,
    verdicts: list[dict[str, Any]] | str | None = None,
    directory_context: bool = True,
) -> dict:
    """A working order for improving a brief with your own model, gate first.

    Pass the verdicts you already have (the JSON array from your model) to
    target the failing rules in weight order; without them the prompt walks
    every rule. The prompt keeps the author's voice and forbids invented
    scores and facts. Nothing is generated here: your model does the writing.
    """
    parsed = _verdict_list(verdicts) if verdicts else None
    return await _free(ctx, lambda: byo.improvement_prompt_payload(brief, parsed, directory_context))


@server.tool(annotations=READ_ONLY)
async def check_brief(ctx: Context, brief: str, directory_context: bool = True) -> dict:
    """Deterministic checks only — semantic coverage is INCOMPLETE. Never a score.

    Finds what a pattern can find for certain: emails, URLs and phone numbers
    (which block anonymisation), a stated budget and timeline, personal-data
    cues without a compliance cue, unfilled placeholders, the title line and
    labelled sections. It does not judge meaning: company or person names, a
    vague problem or an unmeasurable goal pass straight through. Use it as a
    quick pre-flight, then judge with get_judge_prompt and aggregate_verdicts.
    """
    return await _free(ctx, lambda: byo.check_payload(brief, directory_context))


@server.tool(annotations=READ_ONLY)
async def aggregate_verdicts(
    ctx: Context,
    brief: str,
    verdicts: list[dict[str, Any]] | str,
    ruleset_version: str,
    directory_context: bool = True,
) -> dict:
    """Turn your model's verdicts into the bar's score, gate and decision. Advisory.

    Validates the verdicts against the live ruleset (every rule exactly once,
    valid status and confidence, the version you judged at) and against the
    brief (each quote must be copied verbatim), then aggregates them with the
    same engine that scores on the service: same verdicts, same number.
    Any error means no score — fix and resend.

    The result is tagged evaluation_source "client" and authoritative false:
    your model wrote the verdicts, so it is advice, never a welance score, and
    it cannot authorise publication on the welance/directory (the directory
    scores every brief itself). Say so when you report it. Fix gate.missing
    first. directory_context false drops the directory-only policy rules.
    """
    parsed = _verdict_list(verdicts)
    return await _free(ctx, lambda: byo.aggregate_payload(brief, parsed, ruleset_version, directory_context))


@server.tool(annotations=READ_ONLY)
async def bar_status(ctx: Context) -> dict:
    """Which ruleset version is live, and what this free surface can do.

    Confirms the mode (bring your own model, zero provider calls, no fallback
    to welance's model) and the tools available.
    """
    return await _free(ctx, byo.status_payload)


# ---- prompts (with the tool equivalents above for clients that hide prompts) ----


@server.prompt()
def judge_brief(brief: str = "") -> str:
    """The judge prompt with the brief in it: answer with the JSON array, then aggregate_verdicts."""
    return byo.judge_prompt_payload(brief or None)["prompt"]


@server.prompt()
def improve_brief(brief: str = "") -> str:
    """A working order for turning a draft into a publishable brief, with your own model."""
    return byo.improvement_prompt_text(brief)


@server.prompt()
def brief_template() -> str:
    """The brief template built from the live rules, as Markdown to fill in."""
    return byo.template_payload()["template"]


# ---- resources ---------------------------------------------------------------------


@server.resource("perfect-brief://rules", mime_type="application/json")
def rules_resource() -> str:
    """The live ruleset and its arithmetic (same as get_rules)."""
    return json.dumps(byo.rules_payload(), ensure_ascii=False)


@server.resource("perfect-brief://template", mime_type="text/markdown")
def template_resource() -> str:
    """The brief template (same as get_brief_template)."""
    return byo.template_payload()["template"]


@server.resource("perfect-brief://judge-prompt", mime_type="text/plain")
def judge_prompt_resource() -> str:
    """The judge prompt with a {{BRIEF}} placeholder (same as get_judge_prompt without a brief)."""
    return byo.judge_prompt_payload(None)["prompt"]


@server.resource("perfect-brief://verdict-schema", mime_type="application/schema+json")
def verdict_schema_resource() -> str:
    """The JSON Schema a verdict array must meet."""
    return json.dumps(byo.judge_prompt_payload(None)["verdict_schema"])


# =====================================================================================
# The hosted connector: tools that spend the service-funded judge. Separate server,
# separate path (/mcp-hosted), off by default (PB_MCP_HOSTED_ENABLED).
# =====================================================================================

hosted = MCPServer(
    "brief-bar-hosted",
    instructions=(
        "A bar for digital product briefs that the assistant does not control. "
        "Read the rules first, score with the tool, fix the gate before anything "
        "else, and never state a score you did not get from score_brief."
    ),
)

# The API's route handlers, bound by app.main after it has defined them.
_rules: Callable[[], Awaitable[Any]] | None = None
_health: Callable[[], Awaitable[Any]] | None = None
_score: Callable[..., Awaitable[Any]] | None = None
_suggest_all: Callable[..., Awaitable[Any]] | None = None


def bind(*, rules, health, score, suggest_all, free_limit) -> None:
    global _rules, _health, _score, _suggest_all, _free_limit
    _rules, _health, _score, _suggest_all, _free_limit = rules, health, score, suggest_all, free_limit


async def _guarded(ctx: Context, call: Callable[[Request], Awaitable[Any]]) -> Any:
    """Run a route handler as the connector: free limit first, HTTP errors as text."""
    assert _free_limit is not None, "app.main must bind() before the first call"
    request = _request(ctx)
    try:
        await _free_limit(request)
        result = await call(request)
    except HTTPException as exc:  # the API's own refusals, worded for a reader
        # ToolError keeps the message; any other exception is masked by the SDK
        raise ToolError(f"{exc.status_code}: {exc.detail}") from exc
    return result.model_dump() if hasattr(result, "model_dump") else result


@hosted.tool(name="get_rules")
async def hosted_get_rules(ctx: Context) -> dict:
    """Read the bar before judging anything.

    Returns the whole ruleset: every rule's id, human title, the `criteria` the
    judge actually reads, its weight (all weights sum to 100), whether it is
    also a hard gate requirement, and its pinned sources. Also returns the
    engagement floor and the score bands.
    """
    assert _rules is not None
    return await _guarded(ctx, lambda _r: _rules())


@hosted.tool()
async def score_brief(
    ctx: Context,
    brief: str,
    directory_context: bool = True,
    judge: str | None = None,
) -> dict:
    """Score a brief with the service judge (welance's model, rate-limited per address).

    Returns score, band, gate {passed, missing}, decision, one verdict per rule
    with a verbatim quote, and the ruleset_version. Fix `gate.missing` first.
    directory_context False drops the directory-only policy rules. Never report
    a score you did not get from this tool.
    """
    assert _score is not None
    req = ScoreRequest(
        brief=brief,
        locale="en-GB",
        judge=judge,  # type: ignore[arg-type]  # validated by the model
        model=None,
        gate_contexts=None if directory_context else [],
    )
    return await _guarded(ctx, lambda r: _score(req, r, None))


@hosted.tool()
async def suggest_fixes(ctx: Context, brief: str, rule_ids: list[str] | None = None) -> list[dict]:
    """Ready-to-paste insertions for the rules a brief fails, written by the service model
    and reviewed by a second one. Drafts for a human to accept, edit or reject."""
    assert _suggest_all is not None
    from starlette.responses import Response

    req = SuggestAllRequest(brief=brief, rule_ids=rule_ids or None, locale="en-GB", model=None)
    out = await _guarded(ctx, lambda r: _suggest_all(req, r, Response(), None))
    return [s.model_dump() if hasattr(s, "model_dump") else s for s in out]


@hosted.tool(name="bar_status")
async def hosted_bar_status(ctx: Context) -> dict:
    """Which ruleset version is live, and whether a real judge is configured."""
    assert _health is not None
    return await _guarded(ctx, lambda _r: _health())


# ---- ASGI ------------------------------------------------------------------------


def _asgi(s: MCPServer):
    """Behind an ingress the Host header is the public domain, so the SDK's
    rebinding guard (meant for localhost servers) is switched off."""
    return s.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )


def asgi_app():
    """The free BYO server, mounted at /mcp."""
    return _asgi(server)


def hosted_asgi_app():
    """The service-judge connector, mounted at /mcp-hosted only when enabled."""
    return _asgi(hosted)
