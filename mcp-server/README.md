# perfect-brief-mcp

A free MCP server that gives your assistant a bar it cannot bend — judged by
**your own model**.

Your model grades the brief with the service judge's own prompt. The bar's
code then validates those verdicts (every rule once, quotes copied verbatim,
the live ruleset version) and computes score, gate and decision with the same
engine the service scores with. welance runs no model for any of these tools.

## Add it to your assistant

Remote, nothing to install — add `https://briefs.welance.com/mcp` as a
connector in Claude, ChatGPT, Cursor or VS Code (see the
[main README](../README.md#mcp-free-bring-your-own-model)).

Local, over stdio:

```json
{
  "mcpServers": {
    "perfect-brief": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/welance/perfect-brief#subdirectory=mcp-server", "perfect-brief-mcp"]
    }
  }
}
```

`brief-bar-mcp` is the same program under its original name.

## What your assistant gets

| tool | what it does |
|---|---|
| `get_rules` | the live catalogue: criteria, weights, gate, policy contexts, arithmetic, version |
| `get_brief_template` | a brief template built from the live rules |
| `get_judge_prompt` | the judge prompt and verdict JSON Schema, for your model to answer |
| `get_improvement_prompt` | a gate-first working order for your model to improve the brief |
| `check_brief` | deterministic checks only — semantic coverage is incomplete, never a score |
| `aggregate_verdicts` | validates your model's verdicts and aggregates them with the service engine |
| `bar_status` | live ruleset version and capabilities |

Prompts: `judge_brief`, `improve_brief`, `brief_template`. Resources:
`perfect-brief://rules`, `perfect-brief://template`,
`perfect-brief://judge-prompt`, `perfect-brief://verdict-schema`.

An aggregated result is **advisory** (`evaluation_source: "client"`): your
model wrote the verdicts, so it is never a welance score and never authorises
publication on the welance/directory, which scores every brief itself.

## Configuration

| variable | default | |
|---|---|---|
| `PB_API` | `https://briefs.welance.com` | point it at your own deployment if you run one |
| `PB_TIMEOUT` | `60` | seconds |
| `PB_HOSTED_TOOLS` | — | `1` also registers `score_brief` and `suggest_fixes`, which use the **service judge** (welance's model, per-address limits) |
| `PB_LLM_KEY` | — | with `PB_HOSTED_TOOLS=1` only: your OpenRouter key, forwarded so those two calls run on your account |
| `PB_JUDGE`, `PB_MODEL` | `llm`, — | with `PB_HOSTED_TOOLS=1` only |

Nothing is stored by this server. What the service keeps — and for how long —
is written out at [briefs.welance.com/data.html](https://briefs.welance.com/data.html).

## Honest limits

It scores **articulation, not truth**, and a client-judged score is only as
honest as the model that wrote the verdicts: the arithmetic is fixed, the
judgement is yours. `check_brief` catches what a pattern can (contact details,
missing budget or timeline labels, placeholders) and nothing that needs
reading for meaning.

MIT. Source, rules and fixtures: [github.com/welance/perfect-brief](https://github.com/welance/perfect-brief).
