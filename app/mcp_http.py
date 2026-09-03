"""The Brief Bar as a hosted MCP connector: `POST /mcp`.

The stdio server in `mcp-server/` runs on the reader's machine and calls the
public API. A chat in the browser (claude.ai, ChatGPT) cannot do that: its
sandbox cannot POST to arbitrary hosts and its fetch tool is GET only. What it
can do is add a remote MCP server as a connector, and then the platform makes
the call, not the sandbox. This module is that server, mounted inside the same
FastAPI app that serves the API, so a release deploys it and nothing changes in
the cluster.

Design:
- Same four tools and the same prompt as the stdio server, word for word; a
  test holds the two in parity.
- The tools call the API's own route handlers in-process. No second code path
  for scoring, and the paid-judge rate limit inside those handlers still
  applies to the calling address.
- Stateless, JSON responses: every tool call is one plain POST with one JSON
  reply, no session to keep and no event stream for the ingress to time out.
- No key handling. A connector runs on the service-funded judge only; bringing
  a key stays a local-machine affair (the stdio server or the API header).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request

from app.models import ScoreRequest, SuggestAllRequest

server = MCPServer(
    "brief-bar",
    instructions=(
        "A bar for digital product briefs that the assistant does not control. "
        "Read the rules first, score with the tool, fix the gate before anything "
        "else, and never state a score you did not get from score_brief."
    ),
)

# The API's route handlers, bound by app.main after it has defined them. Kept
# behind names so this module never imports main (which imports this module).
_rules: Callable[[], Awaitable[Any]] | None = None
_health: Callable[[], Awaitable[Any]] | None = None
_score: Callable[..., Awaitable[Any]] | None = None
_suggest_all: Callable[..., Awaitable[Any]] | None = None
_free_limit: Callable[[Request], Awaitable[None]] | None = None


def bind(*, rules, health, score, suggest_all, free_limit) -> None:
    global _rules, _health, _score, _suggest_all, _free_limit
    _rules, _health, _score, _suggest_all, _free_limit = rules, health, score, suggest_all, free_limit


def _request(ctx: Context) -> Request:
    req = ctx.request_context.request
    if req is None:  # pragma: no cover - only over a non-HTTP transport
        raise RuntimeError("the hosted connector runs over HTTP only")
    return req


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


@server.tool()
async def get_rules(ctx: Context) -> dict:
    """Read the bar before judging anything.

    Returns the whole ruleset: every rule's id, human title, the `criteria` the
    judge actually reads, its weight (all weights sum to 100), whether it is
    also a hard gate requirement, and its pinned sources. Also returns the
    €10k engagement floor and the score bands.

    Call this first when you are helping someone write a brief: the criteria
    are the bar, and quoting them beats paraphrasing them.
    """
    assert _rules is not None
    return await _guarded(ctx, lambda _r: _rules())


@server.tool()
async def score_brief(
    ctx: Context,
    brief: str,
    directory_context: bool = True,
    judge: str | None = None,
) -> dict:
    """Score a brief against the open ruleset. You cannot influence the number.

    Returns:
      score      0-100, a weighted average over the rules
      band       a human label for the score
      gate       {passed, missing} — the hard requirements, separate from the score
      decision   accepted | reserved | blocked
      verdicts   one per rule: status, confidence, and a quote copied VERBATIM
                 from the brief as evidence
      ruleset_version  which bar judged it (the same brief on the same version
                 reproduces the same score)

    A brief can score 92 and still be `blocked` — quality is not admissibility.
    Fix `gate.missing` first, always.

    directory_context: keep True for a brief headed to the welance/Directory
    noticeboard (anonymisation and the €10k floor apply). Set False to score a
    generic digital-product brief without those two policy rules — they drop
    out entirely, and the average renormalises over the rest.

    Never report a score you did not get from this tool.
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


@server.tool()
async def suggest_fixes(ctx: Context, brief: str, rule_ids: list[str] | None = None) -> list[dict]:
    """Get concrete, ready-to-paste insertions for the rules a brief fails.

    Each suggestion is one sentence tailored to this brief's actual domain, and
    is reviewed by a second model before it is returned (`review.accepted`).
    Defaults to every failing or partial rule; pass rule_ids to target some.

    These are drafts for a human to accept, edit or reject — paste them back
    into the brief only with the author's agreement, then re-score.
    """
    assert _suggest_all is not None
    from starlette.responses import Response

    req = SuggestAllRequest(brief=brief, rule_ids=rule_ids or None, locale="en-GB", model=None)
    out = await _guarded(ctx, lambda r: _suggest_all(req, r, Response(), None))
    return [s.model_dump() if hasattr(s, "model_dump") else s for s in out]


@server.tool()
async def bar_status(ctx: Context) -> dict:
    """Which ruleset version is live, and whether a real judge is configured."""
    assert _health is not None
    return await _guarded(ctx, lambda _r: _health())


@server.prompt()
def improve_brief(brief: str = "") -> str:
    """A working order for turning a draft into a publishable brief."""
    return f"""Help me get this brief past The Brief Bar. Work in this order
and do not skip steps:

1. Call `get_rules` and read the criteria. They are the bar; your opinion is not.
2. Call `score_brief`. Report score, band and decision plainly, without softening.
3. If `gate.passed` is false, fix `gate.missing` FIRST. Those block publication at
   any score — a 92/100 brief that names the client is still blocked.
4. Then take the failing verdicts in weight order. For each: quote its verbatim
   evidence, say which criterion it misses, and propose a rewrite of that part in
   the brief's own domain language — no placeholders, no brackets.
5. Re-score after the edits. Repeat until `decision` is "accepted", or until the
   remaining gaps are ones I decide not to fix.

Rules of engagement:
- Never invent, estimate or round a score. It comes from the tool or not at all.
- Do not argue with the gate. It is policy, not an opinion you can outrank.
- Keep my voice. You are raising the floor, not rewriting the brief as yours.

The brief:

{brief or "(paste the brief here)"}"""


def asgi_app():
    """The Starlette app to mount at /mcp. Behind an ingress the Host header is
    the public domain, so the SDK's rebinding guard (meant for localhost
    servers) is switched off."""
    return server.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
