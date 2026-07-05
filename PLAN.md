# PLAN — from this zip to a live, public OSS service

**Goal.** Publish this repo as **github.com/welance/perfect-brief** (public,
MIT), publish the explanatory + try-it pages from `site/`, and deploy the API to
**briefs.welance.com** on the Welance cloud (OVH k8s), following the rules in
the local **wegitlab** project. The Directory (welance.com/directory) then
consumes the API; it holds no scoring logic.

Everything in this repo is already built and verified (engine, API, console,
tests, Docker). Your job is **recon → publish → deploy → wire**, not rebuild.
Work the phases in order; each has a hard acceptance check. Commit per phase.

---

## Phase 0 — Recon (read-only, no code changes)
1. Read the **wegitlab** project on this machine: registry, ingress + DNS
   conventions, secrets management, CI/CD pipeline norms, anything mandatory
   for new services on the Welance OVH cloud.
2. Scan existing Welance platform repos for a FastAPI/containerised-service
   deploy pattern already in use. Prefer reuse over invention.
3. Decide: GitHub Pages from `site/` vs the Welance-standard static publishing
   (whichever wegitlab norms indicate). Default: GitHub Pages, branch `main`,
   folder `/site` (rename to `/docs` only if Pages requires it).

**Acceptance:** a `NOTES.md` (≤ 30 lines) at repo root stating: chosen deploy
path, registry, ingress/DNS plan, secrets mechanism, pages mechanism. Nothing
else changed.

## Phase 1 — Publish the public repo
1. Create **github.com/welance/perfect-brief**, push this tree as-is
   (LICENSE, GOVERNANCE.md, CONTRIBUTING.md, CODEOWNERS are already at root).
2. `.github/workflows/ci.yml` is included and must be green on first push
   (ruff + mypy + pytest, all offline on the mock judge).
3. Repo description: *"Score a digital product brief against an open,
   versioned ruleset. The LLM only judges; code owns the numbers, the gate,
   and the publish decision."*

**Acceptance:** public repo exists, CI green, README renders correctly.

## Phase 2 — Publish the pages
1. Enable Pages (per Phase 0 decision) serving `site/`:
   `index.html` (landing — the voice reference), `console.html` (interactive
   scorer, mock works offline), `rules.html` (the 14 rules + governance),
   `article.md` (the long-form source).
2. Verify relative links between the three pages work on the published origin.

**Acceptance:** a public URL serves all three pages; console scores the
presets offline (mock) with no key.

## Phase 3 — Deploy the service to briefs.welance.com
1. Follow wegitlab rules **exactly**: build the image, push to the Welance
   registry, k8s `Deployment` + `Service` + `Ingress` (or the platform-repo
   pattern found in Phase 0), liveness/readiness on `GET /v1/healthz`.
2. Redis: small single instance or managed — it is an ephemeral cache
   (`docker-compose.yml` shows the exact flags: no persistence, LRU).
3. Secrets: `PB_ANTHROPIC_API_KEY` via the wegitlab-sanctioned mechanism.
   Set `PB_DEFAULT_JUDGE=mock`, `PB_CORS_ORIGINS` locked to
   `https://welance.com` + the pages origin. DNS: `briefs.welance.com`.

**Acceptance:** `curl https://briefs.welance.com/v1/healthz` → `status:ok`,
`llm_configured:true`; the `make score` demo body returns `decision:"blocked"`
with `anonymised` in `gate.missing` against production.

## Phase 4 — Wire the console's live mode to the service
The consoles (`app/static/index.html` and `site/console.html` — keep them
identical) currently call Anthropic directly from the browser for the live
judge and the fix suggestions. Replace those three call sites with the service:
- live judging → `POST {API}/v1/score {brief, locale, judge:"llm"}` and map
  `verdicts[]` into the existing render path (fields already match);
- per-gap fixes → `POST {API}/v1/suggest {brief, rule_id, locale}`;
- fix-all → `POST {API}/v1/suggest/all {brief, locale}`.
`API` = same-origin when served by the service, `https://briefs.welance.com`
when on Pages (one const at the top). Keep the mock as the offline fallback and
keep the mock path byte-identical (do not touch `judge()`/`aggregate()` in JS).

**Acceptance:** on the public Pages console, the live toggle scores a brief
with no key in the client (network tab shows only briefs.welance.com);
`make test` still green.

## Phase 5 — Hand the contract to the Directory
No code in this repo. Open an issue (or draft PR) on the directory repo with:
the `POST /v1/score` contract (README has the exact shape), the debounce +
on-submit pattern, and the requirement to persist `verdict + ruleset_version`
via otto.welance.com for a reproducible audit trail.

**Acceptance:** issue filed with the snippet; link recorded in `NOTES.md`.

---

## Token discipline (read once, apply always)
- **Trust the tests.** Engine verified: fixtures 5/5, JS↔Python parity, ruff +
  mypy clean. If `make test` is green, the engine is right — do not re-derive.
- **Surgical edits only** on the HTML consoles; never regenerate them.
- Prefer reading wegitlab/platform repos over asking; ask only when a deploy
  rule is genuinely ambiguous or credentials are missing.
- Don't add features not in this plan (no DB, no auth system, no rewrite in
  another language). The service is deliberately stateless.
- Public prose: follow the voice of `site/index.html` — modest, professional,
  sincere, confident. The one-line story: *20% brief, 80% team; this scores
  the 20% so senior cross-functional teams can deliver the 80%.*

## Definition of done
All five acceptance checks true · CI green on the public repo · pages live ·
`briefs.welance.com/v1/healthz` live · console live-mode keyless in the client.
