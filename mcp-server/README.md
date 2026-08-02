# perfect-brief-mcp

An MCP server that gives your assistant a bar it cannot bend.

The score is computed by code from per-rule verdicts against a public, versioned
ruleset — so the model cannot flatter you into a better number — and the gate can
refuse publication outright, which no amount of good prose overturns.

## Add it to your assistant

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

Works with Claude Desktop, Claude Code, Cursor, or anything that speaks MCP.
Nothing to install: `uvx` fetches and runs it. Prefer `pipx`? `pipx run --spec
'git+https://github.com/welance/perfect-brief#subdirectory=mcp-server' perfect-brief-mcp`.

## What your assistant gets

| tool | what it does |
|---|---|
| `get_rules` | the whole bar: criteria, weights, gate requirements, sources |
| `score_brief` | score, band, gate, decision, one verdict per rule with verbatim evidence |
| `suggest_fixes` | ready-to-paste insertions for failing rules, each reviewed by a second model |
| `bar_status` | which ruleset version is live |

Plus an `improve_brief` prompt that enforces the working order: read the rules,
score, fix `gate.missing` first, quote the evidence, re-score — and never state a
score that did not come from the tool.

## Configuration

| variable | default | |
|---|---|---|
| `PB_API` | `https://briefs.welance.com` | point it at your own deployment if you run one |
| `PB_JUDGE` | `llm` | `mock` is the offline keyword stub (English only) |
| `PB_LLM_KEY` | — | your OpenRouter key. **With your key we run no model for you** — the call is forwarded and billed to your account |
| `PB_MODEL` | — | model override; with your own key, any model at all |
| `PB_TIMEOUT` | `120` | seconds |

Nothing is stored by this server. What the service itself keeps — and for how
long — is written out plainly at
[briefs.welance.com/data.html](https://briefs.welance.com/data.html).

## Honest limits

It scores **articulation, not truth**: a beautifully written brief for a doomed
product will score well. What you get is narrower and more useful than a verdict
on your idea — a number two people obtain the same way, a gate that refuses on
policy rather than taste, and a vocabulary you can argue in.

MIT. Source, rules and fixtures: [github.com/welance/perfect-brief](https://github.com/welance/perfect-brief).
