# Changelog

All notable changes to perfect-brief are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org). The **ruleset** carries its own version
(`semver+content-digest`, e.g. `1.0.0+83107bae`) independent of the service
version below — a rule change bumps the ruleset, a service change bumps this.

## [1.8.0] - 2026-08-19

### Added
- **The operator covenant — the rules judge briefs, `OPERATOR-COVENANT.md`
  judges us.** welance writes the bar, runs the noticeboard it gates, and
  pitches on that noticeboard as a team. Openness constrains the bar; nothing
  constrained the operator. Eight commitments now do — no lead-mining, no
  training on briefs, no reading-room on the cache, the same bar for our own
  briefs, fees at cost — each labelled with how it is enforced: CI-tested where
  code can reach it, named plainly where it cannot. It is linked from every
  page that asks for trust.
- **The landing is the first tap, not an argument.** The hero carries a paste
  box and one button; the brief rides to the console in a single localStorage
  key, read once and removed on boot, and arrives already scored by the offline
  mock. No new scoring surface, no signup, nothing stored — and the box says so
  in its own margin. Whoever has no brief yet gets the other door in the same
  breath: build it on the Directory, guided.

### Changed
- **The name drops "perfect": The Brief Bar.** The copy always called it the
  bar; the name now agrees — The Brief Bar · Price Split · Team Rate, across
  the lockup, ten pages, nine console dictionaries and eight locales. The rules
  page heads "The bar for digital product briefs". Code identifiers, the
  package and the repository keep their names.
  The MCP server follows in the two places it speaks to a reader: its package
  description and the prompt it hands an assistant.
- **The honesty pass that ships with the name.** The conflict of interest
  leaves the fine print and is said where objections land — welance pitches on
  the Directory too, same fees, same blindness, same bar, and the
  `ruleset_version` on every verdict proves nobody got a different one.
  `data.html` stops claiming "never stored" where quotes survive 24h, owns the
  per-IP counters, and pins its no-third-party claim to a test (lottie is
  vendored; the e2e host allowlist tightened to match). The reproducibility
  overclaim becomes the inspectable truth: temperature 0 is not determinism,
  and the verbatim evidence is what never expires.
- **Ruleset 1.1.0 — `anonymised` judges identity, not specificity.** The gate
  was blocking publishable briefs for naming the compliance regime ("GDPR is a
  named regulation/brand") while `data-compliance`, in the same run, was
  passing them for exactly that; it also read a concrete description of the
  business ("a wholesaler of chilled goods, forty routes, two warehouses") as
  "company details". Both are what the rest of the ruleset asks a brief to
  contain. The criteria now says so: laws, standards and certifications are
  not brands, sector and size and volumes are not identity, and the rule fails
  only when a reader could tell WHO wrote the brief. Found on nine non-English
  starter briefs for the Directory, every one of them blocked on this rule
  alone. `tests/test_anonymised_llm.py` is the live regression — MockJudge
  cannot exercise a prompt change.

### Fixed
- **The offline mock admits, in any language, that it reads English.** The
  keyword mock warned only when the interface language was switched, so a brief
  pasted in Italian under the English UI got a confident, meaningless number
  from a matcher that had read nothing. It now looks at the brief's own
  language — a non-Latin script, or unmistakably-not-English function words
  outnumbering English ones — using two signals rather than one threshold,
  because a terse English brief has few function words in absolute terms.
  Validated against both presets and five languages. This matters more now that
  the landing is paste-first: the first thing a visitor does is paste, in
  whatever language they think in.

## [1.7.0] - 2026-08-12

The pages take the Directory's branding, and the console stops pretending the
AI judge answered when it did not.

### Changed
- **Branding ported from welance/Directory.** The header carries the mark and
  the project name alone; the full welance lockup lives in the footer, which
  grows a start-here column, the model, build-with-it, and the two legal
  entities. An MIT ruleset meant to be common property should not co-brand
  every page, and the reasoning — including two decisions revised mid-flight —
  is in `docs/superpowers/specs/2026-08-09-directory-branding-port-design.md`.

### Added
- **The console separates the judge you asked for from the judge that
  answered.** When a live call fails it re-runs the keyword judge, warns, and
  leaves a standing line under the score saying so. It deliberately does not
  drop the reader out of live mode: that would hide the key field and the model
  selector, which is exactly what someone whose call just failed reaches for.
  This matters today — `judge=llm` returns 504 in production on an ingress
  timeout, and the page used to hide it.

### Fixed
- `integrate.html` no longer claims a pasted prompt reaches the API from a
  browser chat — it does not, and saying so was wrong.
- `PB_CORS_ORIGINS` gained `www.welance.com`.

## [1.6.2] - 2026-08-09

### Fixed
- **A per-role rate can be typed again.** On the team page, entering a rate of
  more than one digit was effectively impossible: the field lost focus after
  every keystroke. Each `input` event called `render()`, and `render()` clears
  `#rows` and rebuilds every row — destroying the very element being typed
  into. It now calls `paint()`, which updates the ceilings in place and is all
  a rate change actually affects. The client rate field was never affected: it
  lives outside `#rows`, so nothing was destroying it.
- **Guarded by `tests/e2e/team-rate-focus.spec.mjs`**, which types a four-digit
  rate and asserts the field is still focused and still holds what was typed.
  It fails against the old code, on desktop and mobile.

## [1.6.1] - 2026-08-09

1.6.0 shipped a page arguing that a claim about your key is worth nothing
unless it is checkable. Read back the next morning, the page overclaimed in
three places and was wrong in one. This fixes all four, because a security page
that is approximately true is worse than none.

### Fixed
- **The page said TLS terminates on our server. It does not.**
  `briefs.welance.com` is behind Cloudflare, so Cloudflare decrypts every
  request — the caller's key included — before a second hop to our origin.
  Three parties see the key, not two, and the honest-limits section now says so
  and names Cloudflare's terms as governing their leg. This was wrong in nine
  languages on the one paragraph whose entire job is admitting what is
  uncomfortable.
- **The canary covered one of the three endpoints that accept `X-LLM-Key`.**
  `/v1/suggest` and `/v1/suggest/all` take the header too and had no leak test
  at all. It is now parametrised over all three, on both the success and the
  provider-rejected path.
- **The canary could not see `print()`.** It walked `caplog.records` — the
  `logging` module only — so a bare `print(api_key)`, the single likeliest form
  of the accidental leak it exists to catch, passed green. It now asserts on
  `capfd` as well. Verified by injecting exactly that leak and watching it turn
  red.

### Changed
- **A 502 no longer echoes the upstream exception to the caller.** It was safe
  only because the exception that happened to arrive was httpx's
  `HTTPStatusError`, whose message carries status and URL. That is safety by
  coincidence of type: swap in an error that quotes the failing request and the
  caller's key is a header on precisely that request. All three handlers now
  return a fixed string and log the detail server-side. Safe by construction.

## [1.6.0] - 2026-08-09

The API asks you to send it an `sk-` key, and until now the only answer to
"why would I do that?" was a paragraph promising we are careful. A promise is
what a sceptical reader discounts, and nothing in the repository failed if it
stopped being true. Both halves of that are now fixed.

### Added
- **`tests/test_byok_leak.py` — the claim as a test.** It drives a real
  `/v1/score` request with a sentinel key, then hunts that sentinel through
  every channel the service can emit on — every log record, the response body,
  the response headers, and everything handed to Redis — and fails unless it
  appears in exactly one place: the `Authorization` header of the outbound
  provider call. A second case forces a 401 from the provider and proves the
  502 error path carries no key. Verified it can fail: a single `log.debug` of
  the key turns both cases red. Its purpose is not today's audit but the
  well-meaning debug line somebody adds next year.
- **`site/security.html`** — the same argument for a reader who does not want
  to read Python: the four hops a key takes, the four places it provably is
  not and why each is impossible rather than merely promised, the canary, the
  honest limits, and what to do instead. Linked from `data.html`,
  `SECURITY.md`, the README, and the console's key field. Prose is translated
  into all eight locales; file paths, function names and test names are not,
  so a drifting translation can soften a sentence but never contradict the
  code beside it.

### Fixed
- **The Redis URL is no longer logged.** `cache.connect` printed it at INFO on
  every boot; if that URL carries a password, our own secret was going to
  stdout.

### Changed
- **Both pages now admit that bring-your-own-key verdicts are cached.** The
  no-cache guard only ever existed on the suggestion path, so a `/v1/score`
  call made with your key reads and writes the shared verdict cache. No key
  material reaches Redis and a cache entry can only be hit by somebody who
  already has the exact brief text — but the verdict you paid for can serve
  someone else. `data.html` said nothing about this; once a page invites
  scrutiny, silence reads as concealment.

## [1.5.1] - 2026-08-02

A release nobody could see. 1.5.0 deployed correctly — right commit, right
image, right tag — and then sat behind an hour of cached JavaScript. Asking a
cache politely turned out not to be enough, so the address of an asset is now
derived from the asset itself.

### Fixed
- **Assets are served at an address made from their own bytes.** Every page is
  rewritten on the way out to point at `/a/<digest>/welance.css`, cached for a
  year and marked `immutable`. When a file changes, its address changes, and
  the old one is simply never requested again — no cache anywhere has to be
  told anything, and there is no configuration to get right.
- **Pages are never cached** (`Cache-Control: no-cache`): a page is how a new
  build announces itself, so it must always be fresh.
- **Query-string cache-busting removed.** The `?v=N` suffixes are gone. They
  were manual, easy to forget, and a CDN may cache ignoring the query string.
  Headers alone would not have been enough either — staging showed our
  `no-cache` rewritten to `max-age=14400` before it reached the browser.
- The plain paths (`/chrome.js`) still work untouched, so the same `site/`
  files keep working on GitHub Pages and when opened from disk.

### Changed
- **The effort split is a bar you drag.** On Perfect Team the shares are no
  longer free-standing weights read as parts of whatever they happen to add up
  to. They are percentages of one project, and a handle sits on every boundary:
  drag it and effort moves from one role to its neighbour, so the total cannot
  leave 100 — on a phone as on a laptop, with the keyboard as with a thumb.
  The per-role number field is gone: the split has one home, not two.
- **The split bar is deliberately colourless.** It is something you set, not
  something the model concluded, so it uses a neutral ramp mixed from the
  page's own ink; the brand's colours stay spent on the result below, where
  they mean something.
- **"Find a team" stays on the phone.** The one link that leads out of the
  page was being dropped below 560px. It now holds at 320px in all eight
  languages — the language switch shortens to its flag and code when closed
  (the list still names every language in full), and on the narrowest screens
  the theme toggle stands down, since the theme follows the system anyway.
- **The header lost its glyph**, and holds its shape at every width — it had
  been overflowing on tablets (134px at 1024px) since the machine was drawn.
- **welance is all-lowercase, everywhere.** In every language and every
  position, including the first word of a sentence; only the JavaScript
  identifiers a language forces (`WelanceI18n`, `WelancePricing`) keep their
  capital. A test enforces it across the public pages.

## [1.5.0] - 2026-08-02

The bar becomes something you can put inside your own tools — and the project
starts standing on its own name rather than ours.

### Added
- **MCP server** (`mcp-server/`): a local stdio server over the public API with
  four tools — `get_rules`, `score_brief`, `suggest_fixes`, `bar_status` — and
  an `improve_brief` prompt that enforces the working order (read the rules,
  fix the gate first, quote the evidence, re-score) and forbids inventing a
  score. `PB_LLM_KEY` brings your own key: with it, we run no model for you.
- **`integrate.html`**: four routes to the same bar — console, paste a prompt,
  connect MCP, call the API — each labelled with who it is for and how long it
  takes, plus a closing section on what the bar deliberately does not do.
- **`data.html`**: what travels where, what is kept (verdict quotes, 24h) and
  what never is, how to bring your own key, and the custom offer.
- **`no_cache`** on `POST /v1/score`: skip the verdict cache entirely, so
  nothing about a brief is written down — pinned by a contract test, because
  documenting a feature we had not built would have been a lie.
- **Light and dark**, decided before first paint and remembered across pages.
- A **focus-mode invitation** in the console, pointing at the distraction-free
  brief editor on welance/Directory (nine locales).

### Changed
- **Perfect Briefs Machine**, with a stick-drawn mark that shows it: sticks feed
  in, a press stamps a brief, three members snap into a team and leave checked.
  The header leads with the project; welance shrinks to a one-line origin mark.
- **The retained share is named honestly.** On client work it is
  *structure & risk* — it keeps the structure standing and absorbs what goes
  wrong with a client, and the note says plainly that it is not profit and is
  deliberately thin. On internal work it is *welance support*: a colleague's
  real time, which is exactly why the rate drops.
- Contribution guidance is now evidence-first: **do not propose a rule, propose
  the evidence** — a real brief the ruleset scores wrongly, added as a fixture.
  A longer checklist is a weaker one.
- The footer carries two named columns; API docs and source are always one
  click away.

### Fixed
- Internal work no longer reports a client-work share: at full autonomy the
  person keeps 100%, and below it the bar shows the support share instead of a
  margin that does not exist.

## [1.4.0] - 2026-08-02

The welance method, digitalised end to end and opened as a blueprint: the
brief bar was already public, this release adds the two steps that follow it
— what the work is worth, and who does it — plus the narrative that ties
them together, in eight languages.

### Added
- **Perfect Price** (`site/price.html`, now on `welance.css`) and **Perfect
  Team** (`site/team.html`): the split calculator and the missing equation.
  A team is priced like a single independent — roles carry weights, levels
  and their own cost base — and one blended client rate decomposes into four
  visible bands (to the people · headroom · geographic differential ·
  welance margin) that must sum exactly. No-deal is enforced per role: we
  would rather lose an engagement than compress someone below their rate.
- **`site/pricing.js`** — one shared, dependency-free engine holding every
  constant of the model with the reason next to it, plus a formula registry
  the pages *derive* their count from. Pinned by `make test-site`.
- **The method** (`site/method.html`): the problem, Conway's law correctly
  attributed, the three steps, the two doors (Directory maximises
  connections, not margin; welance full service is priced 70/30 and
  guarded by the no-deal rule), the eight formulas, and the human check
  that no formula can make.
- **Eight languages, one switcher** (`site/i18n.js` + `site/i18n/*.js`):
  en · de · it · ur · pt-BR · vi · ar · es, RTL included, each dictionary a
  flat file a native speaker can correct in a plain PR. Unreviewed
  languages carry a visible `draft` marker.
- **Shared chrome** (`site/chrome.js`): welance.com's header and footer on
  every page, with one call to action — score a brief · compute a split ·
  find a team.
- **Code blocks** (`site/code.js`): language tabs (cURL · JavaScript ·
  Python), one-click copy and a ~50-line highlighter. No build step, no
  dependency; the markup stays plain text so copy yields clean code.
- **`/llms.txt`** and a paste-ready assistant prompt in the console — the
  bar, addressed to machines: never invent a score, call the API.
- **The judge's language guarantee**: one line in the prompt makes it
  explicit, and `make test-llm-multilingual` proves it — the same brief in
  eight languages must reach the same gate decision and a score within a
  declared tolerance (llm-only, outside offline CI).
- **Tests as promises**: `tests/test_contract.py` pins the public API shape
  and its invariants for OSS consumers; `tests/e2e` drives the real service
  with Playwright (both calculators, every internal link, no unexpected
  external host, the language following you across pages). `make test-e2e`,
  `make test-all`.

### Changed
- **`/docs` explains itself**: every schema field carries a one-line
  description and, where it helps, an example.
- Public copy follows welance.com's rhythm — a short claim, one paragraph,
  the depth one click down in the fine print. Two e2e tests keep it that
  way: nothing on the surface over 360 characters.
- The brand is lowercase everywhere it is written: **welance**.
- Founding year stated consistently as 2011.

### Fixed
- The gate requirement value is `not_fail`; `rules.html` and the API
  description both said `not-fail`. Caught by the new contract suite.
- **Internal work showed a person share of 70%.** There is no client and
  therefore no split: the person keeps all of it, and what the level moves
  is the ceiling, not anyone's cut. The figure now reads 100% and the
  formula line stops naming a share that does not exist.

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
