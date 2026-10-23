"""Perfect Brief — MCP server over stdio (free, bring your own model).

Gives an assistant one thing it cannot give itself: a bar it does not control.
Your own model judges the brief with the service judge's own prompt; the
bar's own code turns those verdicts into score, gate and decision. welance
runs no model for any of these tools. Results are client-judged and advisory:
only the welance/directory's own scoring can publish a brief.

Runs locally over stdio and talks to the public API at briefs.welance.com
(`/v1/byo/*`, which never calls a model). Nothing is stored here. The same
tools are served remotely at https://briefs.welance.com/mcp.

    PB_API          base URL      (default https://briefs.welance.com)
    PB_TIMEOUT      seconds       (default 60)

Legacy, opt-in: PB_HOSTED_TOOLS=1 also registers `score_brief` and
`suggest_fixes`, which call the service judge (`/v1/score`, `/v1/suggest/all`).
They spend welance's model under its per-address limit unless PB_LLM_KEY
carries your own OpenRouter key, which is then forwarded for that call.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

API = os.environ.get("PB_API", "https://briefs.welance.com").rstrip("/")
TIMEOUT = float(os.environ.get("PB_TIMEOUT", "60"))
HOSTED_TOOLS = os.environ.get("PB_HOSTED_TOOLS") == "1"
JUDGE = os.environ.get("PB_JUDGE", "llm")
LLM_KEY = os.environ.get("PB_LLM_KEY") or None
MODEL = os.environ.get("PB_MODEL") or None

INSTRUCTIONS = (
    "Perfect Brief: an open bar for digital product briefs, free, with your own model. "
    "Read the rules (get_rules), judge the brief with your own model using get_judge_prompt, then "
    "send your JSON verdicts to aggregate_verdicts: the bar's own code computes score, gate and "
    "decision. Fix the gate first. Never state a score you did not get from aggregate_verdicts, and "
    "say it is client-judged and advisory: only the welance/directory's own scoring can publish. "
    "Privacy: https://briefs.welance.com/privacy.html. Terms: https://briefs.welance.com/terms.html."
)

READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
# The opt-in service-judge tools (score_brief, suggest_fixes) change nothing either,
# but they send the brief to a model provider through OpenRouter: open world.
SERVICE_JUDGE = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
)

server = MCPServer(
    "perfect-brief",
    title="brief bar",
    website_url="https://briefs.welance.com",
    instructions=INSTRUCTIONS,
)


def _headers(byok: bool = False) -> dict[str, str]:
    h = {"content-type": "application/json"}
    if byok and LLM_KEY:  # only ever on the opt-in legacy tools
        h["x-llm-key"] = LLM_KEY
    return h


async def _post(path: str, payload: dict[str, Any], byok: bool = False) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{API}{path}", json=payload, headers=_headers(byok))
        if r.status_code >= 400:
            raise RuntimeError(f"{r.status_code}: {r.text[:500]}")
        return r.json()


async def _get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{API}{path}")
        r.raise_for_status()
        return r.json()


def _verdict_list(verdicts: list[dict[str, Any]] | str) -> Any:
    """Models often hand over their answer as the JSON text they wrote. Accept both."""
    if isinstance(verdicts, str):
        text = verdicts.strip()
        if text.startswith("```"):
            text = text.strip("`").removeprefix("json").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("verdicts is not valid JSON: send the array your model returned") from exc
    return verdicts


# ---- tools (same names and words as the remote server at /mcp) ----------------


@server.tool(title="Read the brief rules", annotations=READ_ONLY)
async def get_rules() -> dict:
    """Read the bar before judging anything. Free; no model runs.

    Returns the live catalogue with its version: every rule's id, title,
    criteria (what the judge reads), weight, gate role, policy context and how
    to pass it, plus the arithmetic — status scores, confidence threshold,
    accept threshold, bands, the gate and which policy contexts can be turned
    off. The number of rules is whatever the live catalogue says.
    """
    return await _get("/v1/byo/rules")


@server.tool(title="Get a brief template", annotations=READ_ONLY)
async def get_brief_template() -> dict:
    """A brief template built from the live rules, with the inputs each section needs.

    Use it to start a brief from nothing, or to see which section a gap belongs
    in. Markdown, one section per rule, gate rules marked; write in any language.
    """
    return await _get("/v1/byo/template")


@server.tool(title="Get the judge prompt", annotations=READ_ONLY)
async def get_judge_prompt(brief: str = "") -> dict:
    """The judge prompt and verdict JSON Schema, for YOUR model to answer. Free.

    This is the service judge's own prompt, word for word, so your model grades
    against the same bar. Pass the brief to get it embedded, or leave it empty
    for a template with a {{BRIEF}} placeholder. Answer the prompt with your
    own model (temperature 0 if you can), return only the JSON array it asks
    for, and send that array with the brief and the returned ruleset_version to
    aggregate_verdicts. welance runs no model for this.
    """
    return await _post("/v1/byo/judge-prompt", {"brief": brief or None})


@server.tool(title="Get an improvement prompt", annotations=READ_ONLY)
async def get_improvement_prompt(
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
    payload: dict[str, Any] = {"brief": brief, "directory_context": directory_context}
    if verdicts:
        payload["verdicts"] = _verdict_list(verdicts)
    return await _post("/v1/byo/improvement-prompt", payload)


@server.tool(title="Run deterministic checks", annotations=READ_ONLY)
async def check_brief(brief: str, directory_context: bool = True) -> dict:
    """Deterministic checks only — semantic coverage is INCOMPLETE. Never a score.

    Finds what a pattern can find for certain: emails, URLs and phone numbers
    (which block anonymisation), a stated budget and timeline, personal-data
    cues without a compliance cue, unfilled placeholders, the title line and
    labelled sections. It does not judge meaning: company or person names, a
    vague problem or an unmeasurable goal pass straight through. Use it as a
    quick pre-flight, then judge with get_judge_prompt and aggregate_verdicts.
    """
    return await _post("/v1/byo/check", {"brief": brief, "directory_context": directory_context})


@server.tool(title="Score from your verdicts", annotations=READ_ONLY)
async def aggregate_verdicts(
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
    return await _post(
        "/v1/byo/aggregate",
        {
            "brief": brief,
            "verdicts": _verdict_list(verdicts),
            "ruleset_version": ruleset_version,
            "directory_context": directory_context,
        },
    )


@server.tool(title="Bar status", annotations=READ_ONLY)
async def bar_status() -> dict:
    """Which ruleset version is live, and what this free surface can do.

    Confirms the mode (bring your own model, zero provider calls, no fallback
    to welance's model) and the tools available.
    """
    return await _get("/v1/byo/status")


# ---- prompts ---------------------------------------------------------------------


@server.prompt(title="Judge a brief")
async def judge_brief(brief: str = "") -> str:
    """The judge prompt with the brief in it: answer with the JSON array, then aggregate_verdicts."""
    return (await _post("/v1/byo/judge-prompt", {"brief": brief or None}))["prompt"]


@server.prompt(title="Improve a brief")
async def improve_brief(brief: str = "") -> str:
    """A working order for turning a draft into a publishable brief, with your own model."""
    if not brief.strip():
        brief = "(paste the brief here)"
    return (await _post("/v1/byo/improvement-prompt", {"brief": brief}))["prompt"]


@server.prompt(title="Brief template")
async def brief_template() -> str:
    """The brief template built from the live rules, as Markdown to fill in."""
    return (await _get("/v1/byo/template"))["template"]


# ---- resources -------------------------------------------------------------------


@server.resource("perfect-brief://rules", title="Rules", mime_type="application/json")
async def rules_resource() -> str:
    """The live ruleset and its arithmetic (same as get_rules)."""
    return json.dumps(await _get("/v1/byo/rules"), ensure_ascii=False)


@server.resource("perfect-brief://template", title="Brief template", mime_type="text/markdown")
async def template_resource() -> str:
    """The brief template (same as get_brief_template)."""
    return (await _get("/v1/byo/template"))["template"]


@server.resource("perfect-brief://judge-prompt", title="Judge prompt", mime_type="text/plain")
async def judge_prompt_resource() -> str:
    """The judge prompt with a {{BRIEF}} placeholder (same as get_judge_prompt without a brief)."""
    return (await _post("/v1/byo/judge-prompt", {"brief": None}))["prompt"]


@server.resource(
    "perfect-brief://verdict-schema", title="Verdict schema", mime_type="application/schema+json"
)
async def verdict_schema_resource() -> str:
    """The JSON Schema a verdict array must meet."""
    return json.dumps((await _post("/v1/byo/judge-prompt", {"brief": None}))["verdict_schema"])


# ---- legacy, opt-in: the service judge -------------------------------------------


async def score_brief(brief: str, directory_context: bool = True, judge: str | None = None) -> dict:
    """Score a brief with the service judge (welance's model, rate-limited per address).

    With PB_LLM_KEY set the call runs on your own OpenRouter account instead.
    Fix `gate.missing` first. Never report a score you did not get from this tool.
    """
    payload: dict[str, Any] = {"brief": brief, "judge": judge or JUDGE}
    if MODEL:
        payload["model"] = MODEL
    if not directory_context:
        payload["gate_contexts"] = []
    return await _post("/v1/score", payload, byok=True)


async def suggest_fixes(brief: str, rule_ids: list[str] | None = None) -> list[dict]:
    """Ready-to-paste insertions for failing rules, written by the service model (or your key's)."""
    payload: dict[str, Any] = {"brief": brief}
    if rule_ids:
        payload["rule_ids"] = rule_ids
    if MODEL:
        payload["model"] = MODEL
    return await _post("/v1/suggest/all", payload, byok=True)


def register_hosted_tools(target: MCPServer) -> None:
    target.tool(title="Score with the service judge", annotations=SERVICE_JUDGE)(score_brief)
    target.tool(title="Suggest fixes", annotations=SERVICE_JUDGE)(suggest_fixes)


if HOSTED_TOOLS:
    register_hosted_tools(server)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
