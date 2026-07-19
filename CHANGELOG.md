# Changelog

All notable changes to perfect-brief are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org). The **ruleset** carries its own version
(`semver+content-digest`, e.g. `1.0.0+83107bae`) independent of the service
version below — a rule change bumps the ruleset, a service change bumps this.

## [1.3.0] - 2026-07-19

### Added
- **Gate contexts**: `anonymised` and `budget-floor` are welance/Directory
  noticeboard policy, not properties of a good generic brief. Both rules and
  their gate entries carry `context: directory`; a caller deactivates the
  context per request (`gate_contexts: []`) and they drop out entirely — no
  gate, no score weight, the average renormalised. Verdicts are never
  changed. Additive API: `gate_contexts` on `POST /v1/score`,
  `gate.contexts` in the response (audit trail). The console grows a
  Directory-context toggle under the publish gate (all locales); fixture
  0006 pins the behavior.
- **The perfect-brief Lottie** (`site/animations/the-perfect-brief.json`):
  hand-authored ident in the welance house animation format, played on the
  landing with the CSS stroke-draw SVG as no-JS / reduced-motion fallback.

### Changed
- **welance/Directory visual DNA** across all public pages: shared
  `site/welance.css` (Directory tokens, buttons, animated asterisk
  wordmark), Maison Neue loaded from welance.com (no font binaries in the
  repo), breadcrumb navigation, one 1200px container, GitHub repo button
  first in the hero.
- **One public surface**: the FastAPI service now mounts `site/` at `/` —
  the same pages GitHub Pages publishes (landing, console, rules).

### Removed
- `app/static/index.html` console fork (its verifier badges and
  attribute-safe escaping were ported into `site/console.html` first).

## [1.2.0] - 2026-07-17

### Added
- **Suggestion verifier loop** ("the verifier of the verifier"): every AI
  suggestion is screened by a second model against three criteria — anchored,
  on-rule, actionable. Rejected suggestions are regenerated with the
  reviewer's critique fed back (max 2 retries); the final attempt ships with
  its rejected review attached. Verifier failure never fails a request —
  suggestions return unscreened and flagged.
- Screening metadata on `/v1/suggest[/all]`: per-suggestion `review`
  (`accepted`, `reason`) and `verifier_model` fields (additive), plus
  `X-PB-Screened`, `X-PB-Iterations`, `X-PB-Verifier-Model` response headers.
- `PB_VERIFIER_MODEL` setting: explicit slug, or `auto` = first allowlist
  model from a different vendor than the judge (cross-lab review by
  construction).
- Suggestion result cache keyed by
  `(ruleset_version, judge_model, verifier_model, sha256(brief), rule_ids, locale)`;
  BYOK responses are never cached.
- Console: ✓/✗ reviewer badges on AI suggestion options, with the reviewer's
  reason on hover.
- Architecture Decision Records: `docs/decisions/0001` (cross-model
  verification) and `0002` (default model selection, with dated price
  snapshot and revisit policy); README "Decisions" section.

### Changed
- Default models are now `deepseek/deepseek-v4-pro` (judge + suggester) and
  `deepseek/deepseek-v4-flash` (verifier) across all environments (ADR 0002).
- `PB_REDIS_URL` defaults to the in-pod sidecar (`redis://localhost:6379/0`)
  in the deployment env files, preparing the redis-as-sidecar consolidation
  (tenant-side change tracked in the platform repos).
- LLM client omits sampling parameters for models that reject non-default
  values (Claude 4.7+/5 family) instead of pinning `temperature: 0`.

### Fixed
- Console `esc()` now escapes single and double quotes: LLM-derived text
  rendered inside HTML attributes (e.g. the reviewer's reason in `title=`)
  could previously break out of attribute context (XSS via prompt injection).

## [1.1.0] - 2026-07-16

First production release — live at <https://briefs.welance.com>.

### Added
- Rules page: accordion with R01–R14 numbering, weight chips, deep links by
  rule id, sources linked from the ruleset's own YAML references.
- Console live mode: calls the service (`/v1/score`, `/v1/suggest[/all]`),
  visible AI-working indicator, live-mode accent, BYOK (`X-LLM-Key`) with
  model picker.
- OpenRouter judge (`app/llm_client.py`): `PB_OPENROUTER_API_KEY` +
  `PB_OPENROUTER_MODELS` allowlist (first = default), `GET /v1/models`,
  model recorded in cache key and response.
- OSS governance: SECURITY.md, Code of Conduct 2.1, issue/PR templates
  (incl. rule-change), Dependabot, CodeQL.
- GitHub → GitLab mirror: push to `main` deploys the develop environment
  (ci.skip + pipeline trigger token).

### Changed
- Production env switched from the direct-Anthropic pattern
  (`PB_ANTHROPIC_API_KEY`/`PB_MODEL`) to the OpenRouter pattern.

## [1.0.0] - 2026-07-06

Initial release (never promoted to production; superseded by 1.1.0).

### Added
- `perfect_brief/` engine: 14 YAML rules with weights summing to 100, gate
  (clear-title, problem-defined, budget-floor, anonymised), deterministic
  scoring/decision in code, mock + LLM judges at temperature 0, fixture
  corpus as the CI gate.
- FastAPI service: `/v1/score`, `/v1/rules`, `/v1/healthz`, redis verdict
  cache + rate limiting (both degrade gracefully), bundled console.
- Public site (`site/`) on GitHub Pages; deploy twin on GitLab with the
  welance git-flow pipeline (develop → staging → production).

[1.2.0]: https://github.com/welance/perfect-brief/releases/tag/v1.2.0
[1.1.0]: https://github.com/welance/perfect-brief/releases/tag/v1.1.0
[1.0.0]: https://github.com/welance/perfect-brief/releases/tag/v1.0.0
