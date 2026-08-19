"""The Brief Bar — MCP server.

Gives an assistant one thing it cannot give itself: a bar it does not control.
The score is computed by code from per-rule verdicts against a public,
versioned ruleset, so the model cannot flatter you into a better number — and
the gate can refuse publication outright, which no amount of good prose can
overturn.

Runs locally over stdio and talks to the public API at briefs.welance.com.
Nothing is stored here. If you set PB_LLM_KEY, that key is forwarded to the
service for the call and used against your own provider account — welance
runs no model for you in that case.

    PB_API      base URL          (default https://briefs.welance.com)
    PB_JUDGE    llm | mock        (default llm; mock is offline, English-only)
    PB_LLM_KEY  your OpenRouter key, optional (bring your own key)
    PB_MODEL    model override, optional (must be in GET /v1/models, or any
                model at all when you bring your own key)
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

API = os.environ.get("PB_API", "https://briefs.welance.com").rstrip("/")
JUDGE = os.environ.get("PB_JUDGE", "llm")
LLM_KEY = os.environ.get("PB_LLM_KEY") or None
MODEL = os.environ.get("PB_MODEL") or None
TIMEOUT = float(os.environ.get("PB_TIMEOUT", "120"))

server = MCPServer(
    "perfect-brief",
    instructions=(
        "A bar for digital product briefs that the assistant does not control. "
        "Read the rules first, score with the tool, fix the gate before anything "
        "else, and never state a score you did not get from score_brief."
    ),
)


def _headers() -> dict[str, str]:
    h = {"content-type": "application/json"}
    if LLM_KEY:
        h["x-llm-key"] = LLM_KEY
    return h


async def _post(path: str, payload: dict[str, Any]) -> Any:
    if MODEL:
        payload.setdefault("model", MODEL)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{API}{path}", json=payload, headers=_headers())
        if r.status_code == 503:
            raise RuntimeError(
                "No judge available. Either the service has no LLM configured, or set "
                'PB_LLM_KEY to your own OpenRouter key, or pass judge="mock" for the '
                "offline keyword stub (English only)."
            )
        r.raise_for_status()
        return r.json()


async def _get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{API}{path}")
        r.raise_for_status()
        return r.json()


@server.tool()
async def get_rules() -> dict:
    """Read the bar before judging anything.

    Returns the whole ruleset: every rule's id, human title, the `criteria` the
    judge actually reads, its weight (all weights sum to 100), whether it is
    also a hard gate requirement, and its pinned sources. Also returns the
    €10k engagement floor and the score bands.

    Call this first when you are helping someone write a brief: the criteria
    are the bar, and quoting them beats paraphrasing them.
    """
    return await _get("/v1/rules")


@server.tool()
async def score_brief(
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
    payload: dict[str, Any] = {"brief": brief, "judge": judge or JUDGE}
    if not directory_context:
        payload["gate_contexts"] = []
    return await _post("/v1/score", payload)


@server.tool()
async def suggest_fixes(brief: str, rule_ids: list[str] | None = None) -> list[dict]:
    """Get concrete, ready-to-paste insertions for the rules a brief fails.

    Each suggestion is one sentence tailored to this brief's actual domain, and
    is reviewed by a second model before it is returned (`review.accepted`).
    Defaults to every failing or partial rule; pass rule_ids to target some.

    These are drafts for a human to accept, edit or reject — paste them back
    into the brief only with the author's agreement, then re-score.
    """
    payload: dict[str, Any] = {"brief": brief}
    if rule_ids:
        payload["rule_ids"] = rule_ids
    return await _post("/v1/suggest/all", payload)


@server.tool()
async def bar_status() -> dict:
    """Which ruleset version is live, and whether a real judge is configured."""
    return await _get("/v1/healthz")


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


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
