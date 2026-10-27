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


def _hints(base: ToolAnnotations, title: str) -> ToolAnnotations:
    """The base hints with the tool's title, which directory listings read from annotations."""
    return base.model_copy(update={"title": title})


# The usage guidance for the free tools lives in a prompt, not in tool descriptions:
# directory policy keeps tool descriptions purely descriptive.
WORKFLOW = """Score this brief against the brief bar with your own model.

1. Call get_rules to read the live catalogue and its arithmetic.
2. Optionally call check_brief for the deterministic pre-flight; it is never a score.
3. Call get_judge_prompt with the brief. Answer that prompt with your own model,
   at temperature 0 if you can, and keep only the JSON array it asks for.
4. Send that array, the same brief and the returned ruleset_version to
   aggregate_verdicts. Any validation error means no score: fix and resend.
5. Fix gate.missing first, then the failing rules in weight order
   (get_improvement_prompt helps with the writing).
6. Report only the score aggregate_verdicts returned, and say that it is
   client-judged and advisory: only the welance/directory's own scoring can
   publish a brief.

The brief:

{brief}
"""

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


@server.tool(title="Read the brief rules", annotations=_hints(READ_ONLY, "Read the brief rules"))
async def get_rules() -> dict:
    """The live brief rules catalogue and its arithmetic. Free; no model runs.

    Returns the live catalogue with its version: every rule's id, title,
    criteria (what the judge reads), weight, gate role, policy context and how
    to pass it, plus the arithmetic — status scores, confidence threshold,
    accept threshold, bands, the gate and which policy contexts can be turned
    off. The number of rules is whatever the live catalogue says.
    """
    return await _get("/v1/byo/rules")


@server.tool(title="Get a brief template", annotations=_hints(READ_ONLY, "Get a brief template"))
async def get_brief_template() -> dict:
    """A brief template built from the live rules, with the inputs each section needs.

    Markdown, one section per rule, with the gate rules marked. It serves as a
    starting point for a new brief and shows which section each gap belongs
    in. Briefs may be written in any language.
    """
    return await _get("/v1/byo/template")


@server.tool(title="Get the judge prompt", annotations=_hints(READ_ONLY, "Get the judge prompt"))
async def get_judge_prompt(brief: str = "") -> dict:
    """The judge prompt and verdict JSON Schema, for a client-side model. Free.

    The prompt is the service judge's own, word for word, so a client-side
    judgement grades against the same bar. With `brief` set, the brief is
    embedded in the prompt; with `brief` empty, the prompt carries a {{BRIEF}}
    placeholder. The response also carries the ruleset_version the prompt was
    built at and the rule ids the verdict array covers. No model runs on
    welance's side.
    """
    return await _post("/v1/byo/judge-prompt", {"brief": brief or None})


@server.tool(title="Get an improvement prompt", annotations=_hints(READ_ONLY, "Get an improvement prompt"))
async def get_improvement_prompt(
    brief: str,
    verdicts: list[dict[str, Any]] | str | None = None,
    directory_context: bool = True,
) -> dict:
    """A prompt for improving a brief with a client-side model, gate rules first.

    `verdicts` is an optional JSON array of verdicts already produced for the
    brief: with it, the prompt targets the failing rules in weight order;
    without it, the prompt covers every rule. The prompt keeps the author's
    voice and forbids invented scores and facts. Only prompt text is returned;
    nothing is generated on welance's side. `directory_context` false drops the
    directory-only policy rules.
    """
    payload: dict[str, Any] = {"brief": brief, "directory_context": directory_context}
    if verdicts:
        payload["verdicts"] = _verdict_list(verdicts)
    return await _post("/v1/byo/improvement-prompt", payload)


@server.tool(title="Run deterministic checks", annotations=_hints(READ_ONLY, "Run deterministic checks"))
async def check_brief(brief: str, directory_context: bool = True) -> dict:
    """Deterministic pattern checks on a brief. Not a score; semantic coverage is incomplete.

    Detects what a pattern can find with certainty: emails, URLs and phone
    numbers (which block anonymisation), a stated budget and timeline,
    personal-data cues without a compliance cue, unfilled placeholders, the
    title line and labelled sections. It does not judge meaning: company or
    person names, a vague problem or an unmeasurable goal are not detected.
    `directory_context` false drops the directory-only policy rules.
    """
    return await _post("/v1/byo/check", {"brief": brief, "directory_context": directory_context})


@server.tool(title="Score from your verdicts", annotations=_hints(READ_ONLY, "Score from your verdicts"))
async def aggregate_verdicts(
    brief: str,
    verdicts: list[dict[str, Any]] | str,
    ruleset_version: str,
    directory_context: bool = True,
) -> dict:
    """The bar's score, gate and decision computed from a client's verdicts. Advisory.

    Validates the verdicts against the live ruleset (every rule exactly once,
    valid status and confidence, the ruleset_version they were judged at) and
    against the brief (each quote must appear in it verbatim), then aggregates
    them with the same engine that scores on the service: the same verdicts
    give the same number. A validation error returns an error and no score.

    The result is labelled evaluation_source "client" and authoritative false:
    the verdicts come from a client-side model, so the score is advisory, is
    not a welance score, and cannot authorise publication on the
    welance/directory, which scores every brief itself. gate.missing lists the
    gate rules not yet met. `directory_context` false drops the directory-only
    policy rules.
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


@server.tool(title="Bar status", annotations=_hints(READ_ONLY, "Bar status"))
async def bar_status() -> dict:
    """The live ruleset version and the capabilities of this free surface.

    Reports the mode (bring your own model, zero provider calls, no fallback
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


@server.prompt(title="Score a brief with your own model")
async def score_with_your_model(brief: str = "") -> str:
    """The workflow: rules, judge prompt, your model's verdicts, aggregate_verdicts, gate first, advisory."""
    return WORKFLOW.format(brief=brief.strip() or "(paste the brief here)")


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
    """Scores a brief with the service judge (welance's model, rate-limited per address).

    With PB_LLM_KEY set, the call runs on that OpenRouter account instead.
    Returns score, band, gate {passed, missing}, decision, one verdict per rule
    with a verbatim quote, and the ruleset_version. `gate.missing` lists the
    gate rules not yet met. `directory_context` false drops the directory-only
    policy rules.
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
    target.tool(
        title="Score with the service judge",
        annotations=_hints(SERVICE_JUDGE, "Score with the service judge"),
    )(score_brief)
    target.tool(title="Suggest fixes", annotations=_hints(SERVICE_JUDGE, "Suggest fixes"))(suggest_fixes)


if HOSTED_TOOLS:
    register_hosted_tools(server)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
