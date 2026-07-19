# CLAUDE.md — perfect-brief

Scoring service + open ruleset for digital product briefs. The **score** (0–100,
weighted average over 14 YAML rules) says how good a brief is; a separate
**gate** (4 hard requirements) says whether it may publish. An LLM only
**judges** (server-side, temp 0); deterministic code owns every number, the
gate, and the decision. Thesis: *20% brief, 80% team* — this scores the 20%.

**Your mission for this session is in `PLAN.md`. Read it first, then Phase 0.**

## Invariants — do not violate
1. **The seam.** The judge returns per-rule verdicts (status/confidence/quote)
   and nothing else. `perfect_brief/score.py` owns weights, gate, decision.
   Never let model output touch a number directly.
2. **Weights sum to 100.** Gate = `clear-title`, `problem-defined`,
   `budget-floor` (not_fail) + `anonymised` (pass). `budget-floor` and
   `anonymised` are Directory noticeboard policy: both the rules and their
   gate entries are tagged `context: directory` and deactivate together per
   request (`gate_contexts: []`) — excluded from gate AND score
   (renormalised); verdicts are never changed. Policy lives in
   `perfect_brief/scoring.yaml` + `rules/*.yaml`, never hardcoded.
3. **Fixtures are the CI gate.** `perfect_brief/fixtures/*.yaml` must stay green
   (`make test`). A ruleset change that moves numbers must update fixtures in
   the same commit, with the reason in the message.
4. **`perfect_brief/` is the future standalone OSS package.** Keep it
   importable with zero service deps inside (no fastapi/redis imports there).
5. **LLM keys server-side only** (`PB_ANTHROPIC_API_KEY` or
   `PB_OPENROUTER_API_KEY`, env). Temperature 0. Per-request model choice is
   restricted to the `PB_OPENROUTER_MODELS` allowlist, and verdicts are cached
   by `(ruleset_version, model, sha256(brief))` — the model is part of the
   audit trail, never a free-text input.
6. The engine is **verified** (fixtures green, JS↔Python parity). Do not
   refactor it, do not rewrite `site/*.html` from scratch — surgical edits
   only. `site/` is the ONE public surface: GitHub Pages publishes it and the
   FastAPI app mounts it at `/` (there is no separate app/static console).

## Commands
`make up` (compose api+redis) · `make test` (fixtures+API, mock judge, no
network) · `make lint` · `make typecheck` · `make dev` · `make health` ·
`make score` (demo: high score but gate-blocked)

## Layout
```
perfect_brief/   engine + ruleset: rules/*.yaml, scoring.yaml, score.py,
                 judge.py (Mock+LLM), llm.py (prompts), fixtures/, loader.py
app/             FastAPI service: main.py (routes), scorer.py (orchestration,
                 Redis cache), settings.py (PB_* env)
site/            THE public pages (landing, console, rules, welance.css,
                 animations) — published by Pages AND mounted by the app at /
tests/           the CI gate. docker-compose.yml = api + redis (cache only).
```

## Environment facts (this machine / Welance)
- The **`wegitlab`** project on this machine documents Welance infrastructure
  and the mandatory rules for deploying new software to the Welance cloud
  (OVH-based Kubernetes). **Read it before writing any deploy config.**
- Check existing Welance platform repos for an adequate stack/CI/deploy pattern
  **before inventing one**; reuse what fits.
- Targets: public repo **github.com/welance/perfect-brief** · service at
  **briefs.welance.com** · public pages from `site/` (GitHub Pages or the
  Welance-standard equivalent per wegitlab).
- Consumers: `welance.com/directory` (Nuxt/TS, pure API consumer) and
  `otto.welance.com` (backend, server-to-server persist of verdicts +
  `ruleset_version`).

## Tone for any public-facing text you write
Modest but professional; sincere and confident. No hype words (revolutionary,
game-changing, AI-powered…). The claim is small and true: a brief you can
score, a bar you can read and change, a gate that keeps the noticeboard blind.
`site/index.html` is the reference for voice.
