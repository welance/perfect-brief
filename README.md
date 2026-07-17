# Perfect Brief — scoring service (`briefs.welance.com`)

Scores a digital product brief against an **open, versioned ruleset**. The score
says *how good* a brief is; a separate **gate** says *whether it may publish*. An
LLM only ever **judges** (server-side, key never leaves the box); deterministic
code owns every number, the gate, and the decision.

This repo is the **service**. The ruleset + engine live inside it as an
installable package (`perfect_brief/`) so they can later be split into their own
OSS repo and consumed here as a pinned dependency — the seam is already drawn.

```
perfect_brief/     the open ruleset + deterministic engine (the OSS core)
  rules/*.yaml       14 rules, weights sum to 100, ★ = gate requirement
  scoring.yaml       the €10k floor, the 4-requirement gate, the bands
  score.py           weighted average + gate + decision (no model here)
  judge.py           MockJudge (keyword, offline) + LLMJudge protocol
  llm.py             batched-judge & suggestion prompts (versioned with rules)
  fixtures/*.yaml    labelled briefs = the regression corpus / CI immune system
app/                 the FastAPI service
  main.py            routes, rate limit, CORS, static console
  scorer.py          mock/LLM orchestration + Redis verdict cache
  static/index.html  the interactive console (the public playground)
site/                the public pages (Pages): landing, console, rules, article
CLAUDE.md · PLAN.md  bootstrap + phased mission for an agentic coding session
GOVERNANCE.md · CONTRIBUTING.md · CODEOWNERS · LICENSE   the open-bar machinery (MIT)
docker-compose.yml   api + redis (the only stateful dependency: ephemeral cache)
```

## Quick start

```bash
cp .env.example .env          # add PB_ANTHROPIC_API_KEY to enable the LLM judge
make up                       # docker compose up --build -d  (api + redis)
make health                   # GET /v1/healthz
open http://localhost:8000    # the console (mock judge works with no key)
```

Without an API key the service runs **mock-only** (instant keyword engine,
fully deterministic) — enough to develop against and to run the whole test
suite. Add the key to unlock the `llm` judge and `/v1/suggest`.

## API

`POST /v1/score`
```json
{ "brief": "…", "locale": "it", "judge": "mock" }   // judge: "mock" | "llm"
```
```json
{ "score": 92.0, "band": "Directory-ready", "decision": "blocked",
  "decision_label": "Blocked — hard requirements unmet",
  "gate": { "passed": false, "missing": ["anonymised"] },
  "verdicts": [ { "rule_id": "anonymised", "status": "fail", "confidence": 0.8,
                  "quote": "Stripe … mara@acme.it", "note": "identifying info present",
                  "weight": 8, "severity": "high", "gate": "pass" }, … ],
  "review_required": false, "low_confidence": [],
  "ruleset_version": "1.0.0+83107baec655", "engine": "perfect-brief@1.0.0+83107baec655",
  "judge": "mock", "cached": false }
```
The `ruleset_version` is your audit trail: it pins exactly which bar judged a
brief, and the score is reproducible against it (LLM judge runs at temperature 0
and is cached by `(ruleset_version, model, brief)`).

The judge's LLM is either direct Anthropic (`PB_ANTHROPIC_API_KEY` + `PB_MODEL`)
or OpenRouter (`PB_OPENROUTER_API_KEY`). With OpenRouter, requests may pick a
`model` from the server's allowlist (`PB_OPENROUTER_MODELS`, exact
vendor-prefixed slugs, comma-separated); anything else is rejected with 422.
The resolved model is returned in every score for a reproducible audit trail.

Bring your own key: send `X-LLM-Key: <your OpenRouter key>` and the call runs
on your key — any model allowed (you pay), used per request, never stored or
logged. Use a spend-capped key. The console exposes this as an optional field
in live mode.

Other endpoints:

- `POST /v1/suggest` `{brief, rule_id, locale, model?}` → tailored fixes for one gap (LLM).
- `POST /v1/suggest/all` `{brief, rule_ids?, locale, model?}` → one fix per failing gap; omit `rule_ids` to auto-detect (LLM).
- `GET /v1/rules` → the full catalogue (id, title, weight, gate, criteria, references) for the directory UI.
- `GET /v1/models` → the enabled judge models (`default` + `available`) for a model picker.
- `GET /v1/healthz` → status + ruleset version + whether the LLM is configured.
- `GET /` → the interactive console.

## How `welance.com/directory` consumes it

The directory is a pure consumer. It renders the verdict; it holds **no** scoring
logic:

```ts
const res = await fetch("https://briefs.welance.com/v1/score", {
  method: "POST",
  headers: { "content-type": "application/json", "x-api-key": KEY },
  body: JSON.stringify({ brief, locale, judge: "llm" }),
}).then(r => r.json());
// res.decision drives publish/blocked/with-reservation; res.gate.missing lists why.
// persist res together with res.ruleset_version for a reproducible audit trail.
```

Score as the user types (debounced) and on submit. `otto.welance.com` calls the
same endpoint server-to-server when it needs to persist a verdict.

## Design notes

- **Stateless service.** The score is a pure function of `(brief, ruleset_version)`.
  There is no database. Redis holds only an ephemeral verdict cache + rate-limit
  counters, and the service degrades gracefully if Redis is down.
- **Ruleset as a dependency.** `perfect_brief/` is an installable package with its
  own version and CI corpus. Today it's vendored here; extracting it to
  `welance/perfect-brief` and pinning a tag is a lift-and-shift, no code change.
- **The gate replaces severity caps.** A critical gap is an explicit publish
  requirement (`clear-title`, `problem-defined`, `budget-floor`, `anonymised`),
  not a quiet penalty on the number.
- **Governance.** Anyone proposes a rule change via PR; the fixture corpus in CI
  is the immune system — a change that moves the numbers must move the fixtures
  too, in the open. Rule-change PRs run on a 7-day community discussion window
  before anyone merges — the PR template walks you through what a complete
  proposal contains, and [GOVERNANCE.md](GOVERNANCE.md) spells out the clock.
  Disagreeing with the bar is a first-class use of this repo.

## Decisions

Architecture decisions with real stakes are recorded as ADRs in
[`docs/decisions/`](docs/decisions/):

- [0001 — cross-model verification](docs/decisions/0001-cross-model-verification.md):
  why a second model reviews every AI suggestion (self-preference bias), and
  why the reviewer currently shares a lab with the generator (cost; one env
  line restores cross-lab review).
- [0002 — default model selection](docs/decisions/0002-default-model-selection.md):
  the criteria, the date-stamped price snapshot behind the DeepSeek V4
  pro/flash pairing, and when to revisit.

## Develop & test

```bash
pip install -e ".[dev]"
make test        # fixture corpus + API tests, all on the deterministic mock judge
make lint        # ruff
make typecheck   # mypy
make dev         # uvicorn --reload on :8000
```

## Deploy (OVH Kubernetes)

The image is a stateless HTTP service on `:8000` with a `/v1/healthz` liveness
probe — a standard `Deployment` + `Service` + `Ingress`, plus a small Redis
(a cache, so a single replica or a managed instance is fine). Set `PB_*` via a
`Secret`/`ConfigMap`; lock `PB_CORS_ORIGINS` to the directory's origin. Scale the
API horizontally; the cache is shared through Redis.

## Note on the console's live judge

The bundled console defaults to the **mock** judge (offline, instant). Its
optional *live* toggle currently calls the Anthropic API directly from the
browser, which only works where a key is available (e.g. claude.ai previews);
when served from this backend it falls back to mock. Wiring the console's live
mode to this service's `/v1/score` + `/v1/suggest` (so the key stays server-side)
is the intended small follow-up.
