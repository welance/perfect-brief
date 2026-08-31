# Brief Bar — scoring service (`briefs.welance.com`)

### → **[briefs.welance.com](https://briefs.welance.com)** — the public pages, live

| | |
|---|---|
| **[Welance Directory](https://welance.com/directory)** | guided brief builder and marketplace powered by this scoring service |
| **[Brief Bar](https://briefs.welance.com/)** | what the service does · **[console](https://briefs.welance.com/console.html)** · **[rules](https://briefs.welance.com/rules.html)** |
| **[Price Split](https://briefs.welance.com/price.html)** | the split calculator — what a role is worth and who gets what part |
| **[Team Rate](https://briefs.welance.com/team.html)** | one blended rate, four visible bands, the no-deal rule |
| **[API docs](https://briefs.welance.com/docs)** | OpenAPI, every field described |
| **[Integrate](https://briefs.welance.com/integrate.html)** | four routes into your workflow: console · prompt · **MCP** · API |
| **[Your brief, your key](https://briefs.welance.com/data.html)** | what travels where, what we keep, and how to bring your own key |
| **[llms.txt](https://briefs.welance.com/llms.txt)** | the bar, written for machines — point your assistant at it |

Eight languages, no build step, no tracking. Same origin serves the pages and
the API.

---

Scores a digital product brief against an **open, versioned ruleset**. The score
says *how good* a brief is; a separate **gate** says *whether it may publish*. An
LLM only ever **judges** (server-side, key never leaves the box); deterministic
code owns every number, the gate, and the decision.

This repo is the **service**. The ruleset + engine live inside it as an
installable package (`brief_bar/`) so they can later be split into their own
OSS repo and consumed here as a pinned dependency — the seam is already drawn.

```
brief_bar/     the open ruleset + deterministic engine (the OSS core)
  rules/*.yaml       14 rules, weights sum to 100, ★ = gate requirement
  scoring.yaml       the €10k floor, the 4-requirement gate (anonymised is directory-context, deactivatable), the bands
  score.py           weighted average + gate + decision (no model here)
  judge.py           MockJudge (keyword, offline) + LLMJudge protocol
  llm.py             batched-judge & suggestion prompts (versioned with rules)
  fixtures/*.yaml    labelled briefs = the regression corpus / CI immune system
app/                 the FastAPI service
  main.py            routes, rate limit, CORS; mounts site/ at /
  scorer.py          mock/LLM orchestration + Redis verdict cache
site/                THE public pages: landing, console, rules — served both
                     by GitHub Pages and by the service itself (one surface)
CLAUDE.md · PLAN.md  bootstrap + phased mission for an agentic coding session
GOVERNANCE.md · CONTRIBUTING.md · CODEOWNERS · LICENSE   the open-bar machinery (MIT)
docker-compose.yml   api + redis (the only stateful dependency: ephemeral cache)
```

## Quick start

```bash
cp .env.example .env          # add a spend-capped PB_OPENROUTER_API_KEY
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
  "ruleset_version": "1.0.0+83107baec655", "engine": "brief-bar@1.0.0+83107baec655",
  "judge": "mock", "cached": false }
```
The `ruleset_version` is your audit trail: it pins exactly which bar judged a
brief, and every verdict carries a verbatim quote from the brief as evidence —
**inspectable** by a human long after any particular model is gone. (The mock
judge is reproducible forever; the LLM judge runs at temperature 0 and is
cached by `(ruleset_version, model, brief)`, but temperature 0 is not a
determinism guarantee across provider updates — the quotes are the part of
the trail that never expires.)

Welance uses OpenRouter (`PB_OPENROUTER_API_KEY`). Publish scoring runs on
`deepseek/deepseek-v4-pro`; interactive suggestion generation runs on
`google/gemini-3.1-flash-lite`. Self-hosters may
still configure the optional direct-Anthropic adapter, but it is not part of
the Welance deployment. With OpenRouter, requests may pick a
`model` from the server's allowlist (`PB_OPENROUTER_MODELS`, exact
vendor-prefixed slugs, comma-separated); anything else is rejected with 422.
The resolved model is returned in every score for a reproducible audit trail.
Suggestion generation may use a lower-latency model selected by
`PB_SUGGEST_MODEL`. Single-rule suggestions are editable human choices and
default to one generation call; set `PB_SUGGEST_VERIFY=true` to restore a
second LLM review. The authoritative score and the multi-gap repair loop keep
their verification behavior. Suggestion responses name their verifier model
when one ran.
The service reuses its OpenRouter connection pool and applies separate bounded
output ceilings (`PB_SUGGEST_MAX_TOKENS`, `PB_SUGGEST_ALL_MAX_TOKENS`, and
`PB_VERIFIER_MAX_TOKENS`) because short suggestion JSON does not need the
judge's larger allowance. Successful service-funded suggestions are cached;
BYOK calls always bypass that shared cache.

The judge normally asks for all fourteen verdicts in one provider call.
`PB_JUDGE_BATCH_SIZE=5` instead runs deterministic 5/5/4 rule batches with at
most `PB_JUDGE_CONCURRENCY=3` calls in flight, then merges them before the same
deterministic aggregation. It is an operational latency option, not a scoring
mode: any incomplete or failed batch refuses the entire score. Keep it at its
default `0` until the live `make test-llm-batching` comparison has passed for
the deployed model.

Bring your own key: send `X-LLM-Key: <your OpenRouter key>` and the call runs
on your key — any valid OpenRouter model slug is allowed unless this deployment
sets `PB_BYOK_MODELS` (you pay), used per request, never stored or logged. BYOK
scoring deliberately bypasses the shared
verdict cache, so the supplied key always funds a fresh call. Use a spend-capped
key. The console exposes this as an optional field in live mode.

Sending a key to somebody else's server deserves more than that paragraph.
Every line that touches it, where it provably is not, and the honest limits are
at [briefs.welance.com/security.html](https://briefs.welance.com/security.html);
the claim is enforced by `tests/test_byok_leak.py`, which fails if the key ever
reaches a log, a cache write, or a response.

Other endpoints:

- `POST /v1/suggest` `{brief, rule_id, locale, model?}` → tailored fixes for one gap (LLM).
- `POST /v1/suggest/all` `{brief, rule_ids?, locale, model?}` → one fix per failing gap; omit `rule_ids` to auto-detect (LLM).
- `GET /v1/rules` → the full catalogue (id, title, weight, gate, criteria, references) for the directory UI.
- `GET /v1/models` → the enabled judge models (`default` + `available`) for a model picker.
- `GET /v1/healthz` → service release, ruleset version, engine + LLM availability.
- `GET /` → the interactive console.

Suggestion responses include `X-PB-Generation-Ms`, `X-PB-Verification-Ms`,
`X-PB-Cached`, `X-PB-Cache-Ms`, `X-PB-Model`, and the standard `Server-Timing` header, so callers
can distinguish model latency from network/UI latency without exposing prompts
or document contents. `/v1/healthz` also reports whether the optional Redis
cache/rate-limit store is currently connected.

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
- **Ruleset as a dependency.** `brief_bar/` is an installable package with its
  own version and CI corpus. Today it's vendored here; extracting it to
  `welance/brief-bar` and pinning a tag is a lift-and-shift, no code change.
- **The gate replaces severity caps.** A critical gap is an explicit publish
  requirement (`clear-title`, `problem-defined`, `budget-floor`, `anonymised`),
  not a quiet penalty on the number.
- **The Operator Covenant.** The rules judge briefs;
  [OPERATOR-COVENANT.md](OPERATOR-COVENANT.md) judges us — no lead-mining, no
  training on briefs, the same bar for welance's own briefs (welance pitches
  on the Directory as a team), with each commitment labelled by how it is
  enforced, CI-tested where code can reach.
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

## Text and document boundary

The API accepts text, not uploads: `brief` is one bounded string. The Directory
may read supported PDF, DOCX and text-family documents locally in the browser
and include their extracted text as untrusted context. Original bytes, images
and arbitrary binaries are not sent to this service, stored by it, or published
as attachments. Multipart publication to Directus is a separate Directory flow.

The bundled console defaults to the **mock** judge (offline, instant). Its live
mode calls this service's `/v1/score` and `/v1/suggest`; provider credentials
stay server-side unless a caller explicitly supplies a per-request BYOK key.
