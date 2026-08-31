# The welance Method, digitalised — Price Split · Team Rate · method page · site-wide i18n

**Date:** 2026-07-31 · **Status:** approved design, pre-implementation
**Owner workstream:** Price Split (second workstream, `PLAN-PRICING.md`)

## 1. What this is

welance, as an agency, has always done one process in person: take an honest
brief, price it transparently, assemble a cross-functional team around it. This
design digitalises that process end to end and opens it as a **blueprint** —
the same move already made for the brief bar. Three public concepts, in
causal order:

1. **Brief Bar** — what the work is. (Live: `index.html`, console, rules.)
2. **Price Split** — what it is worth and who gets what part.
   (Concept + calculator landed; this design publishes them properly.)
3. **Team Rate** — who does it, where in the world, at one blended rate.
   (The missing equation. Built now, not WIP.)

The brief remains **the** principal concept; price and team complement it.

Why it matters, stated once and reused everywhere: a rigid business unit
*adapts itself* to a goal and wastes budget doing so; a cross-functional team
*assembled for* the goal — personally and professionally inclined to it — does
better work. welance experiences and solves this as its principal generalist
problem. Formulas help decide; humans complete the decision (§8).

## 2. Sitemap

```
/            The Brief Bar      (root stays; surgical edits only)
method.html  The three steps        NEW — the narrative/blueprint page
price.html   Price Split          existing; port onto welance.css
team.html    Team Rate           NEW — team calculator
console.html · rules.html           existing
```

- `index.html`: add `method.html` to nav + footer, add the language switcher
  to the header. Nothing else.
- Published URLs do not move. GitHub Pages + FastAPI mount at `/` unchanged.

## 3. Shared engine — `site/pricing.js`

One dependency-free JS file included by `price.html` and `team.html` (as both
already include `welance.css`). Pure policy + math, **no DOM**:

- the three levels with `m(level)` (30/40/50%) and coverage (100/75/50%);
- `share(coverage) = 0.30 + 0.40 × coverage` (the levels are one line, sampled);
- the CoL table with its floor; `payout_local = payout_role × max(coeff, floor)`;
- the no-deal rule as a function: *can this engagement exist?*
  (`R_min = payout / (1 − m)`; client below → no);
- the team equation (§5);
- the **formula registry** (§7).

Every constant carries a comment pointing at the `PRICING.md` section
that justifies it. One copy = when the collective resolves the five open
decisions, one file changes and both pages tell the same truth.

Extraction happens during the Phase-1 port of `price.html` onto `welance.css`,
with a numeric non-regression check: same inputs → exactly today's outputs.

`pricing.js` never touches the brief engine; JS↔Python parity for scoring is
unaffected.

## 4. `price.html` — port, not rewrite

Keep every behaviour (its 5 languages fold into the site i18n of §6, both
themes, per-mode default part sets, dirty tracking, reset). Own component
styles remain only where `welance.css` has no equivalent (split bar, coverage
ladder, parts grid). Breadcrumbs `welance / price split`. Acceptance: sits
beside `console.html` without looking foreign; no numeric regression.

## 5. `team.html` — the missing equation

Same metaphor as `price.html`: the "name" is the **team's** name; the parts
below are the **roles**. Per row: role · weight `wᵢ` (% of project, sum 100) ·
level (AUTONOMOUS / WITH REVIEW / WITH SUPPORT) · CoL coefficient *on the same
page, per row* · the member's own rate (for no-deal).

Outputs, in the order that matters:

```
one blended client rate      R        (input, plus a computed "minimum viable R":
                                       the smallest R that satisfies BOTH every
                                       row's no-deal — pᵢ ≥ member's own rate —
                                       AND the project margin target below)
payout per role              pᵢ = R × share(levelᵢ) × max(colᵢ, floor)
welance margin (project)     1 − Σ wᵢ·shareᵢ·colᵢ   ≥   Σ wᵢ·m(levelᵢ)
```

The client sees **one** rate, not 100 different ones; margins vary inside the
team by level; the project as a whole must clear the **welance margin** — the
named, stated recipe. Inherited, non-negotiable constraints:

a. **CoL differential stays a separate band, own colour**, aggregated at team
   level too — never silently swallowed into margin (`PRICING.md` §7).
b. **No-deal per row**: if at the accepted R any member lands under their own
   rate, the page says so and the engagement does not exist. Nobody is
   compressed to make a margin work (§8 of the concept).
c. Margin target of a mixed team is the **weighted mean of per-level targets**,
   so one role cannot subsidise another's slack.

Also on the page: the "first check" line (§8) and formula tooltips (§7).
English-first with all site languages via §6. Fully anonymised example
defaults — role names only, no people.

## 6. Site-wide i18n — 8 languages

`en` (default) · `de` · `it` · `ur` (RTL) · `pt-BR` · `vi` · `ar` (RTL) ·
`es` (kept: already built in price.html; consistent with the talent-pool
logic of the list).

- **Switcher always present** in every page header, next to the breadcrumb.
  Persisted in `localStorage`, readable from `?lang=`, sets `lang` and `dir`
  on the document. Verify `welance.css` mirrored layout for the two RTL
  languages.
- Mechanics: `site/i18n.js` + one dictionary per language in
  `site/i18n/<lang>.js`, keys via `data-i18n` attributes. English stays as the
  markup text (fallback + SEO); other languages apply on the fly. No build
  step — consistent with the site invariant.
- `price.html` migrates its private switcher to the site system; its existing
  5 translations are reused.
- Console **example prompts localised** in the dictionaries, so the flow can
  be tried in one's own language against the real judge.
- Translations are machine-drafted; **native-speaker review is a per-language
  publication gate** (extends the existing Urdu review of Phase 4: a language
  ships when a native speaker has seen it). Arabic: written UI in Modern
  Standard Arabic, review owned by Palestinian native speakers — their voice
  validates it.
- Honest size note: `rules.html` + `method.html` in 7 extra languages is a lot
  of text. The gate above is what keeps it honest, not speed.

## 7. The formulas, explicit and counted

A **formula registry** lives in `pricing.js`: each formula has an id, a name,
a visual rendering, and a one-line plain-language explanation. Pages *derive*
the list and the count from the registry — "N" is always the exact number,
never a stale promise. Provisional enumeration (**N = 8**; the registry is the
single source of truth and fixes the final count):

1. score — weighted average over the public rules (weights sum 100)
2. gate — the hard requirements, all must hold
3. coverage — role decomposed into parts, scored by both sides
4. `share(level) = 30% + 0.4 × coverage`
5. margin rule — `(R − payout)/R ≥ m(level)`
6. cost of living — `payout_local = payout_role × max(coeff, floor)`
7. no-deal — client won't pay `payout/(1−m)` → the engagement does not happen
8. team equation — blended margin vs weighted target (§5)

Surfacing: in `price.html`/`team.html` every computed number carries a tooltip
with its formula ("formula 6 of 8"); `method.html` renders all of them as
visual blocks. The closing line is the point: **N formulas help make the
decision — everything else is human capital, and it does not compute.**

## 8. The human buffer — "si parte!"

In `method.html`, not a fourth step but a **loop around the third**. The
formulas produce the *starting* team; what they cannot see — cultural
compatibility between members and with the client, kindness, humanity,
availability, stress-handling, the whole mass of soft skills — can only be
learned by actually collaborating. So:

- Work starts for real ("si parte!"), with **scheduled checks** at 1–2–3
  days / weeks / months, scaled to the project's size and complexity, and the
  declared reserve to **replace, remove, or modify** the initial choices.
- **Bidirectional, always**: the independent may not feel right either; every
  human problem must surface fast — that is what prevents resentment, bad
  vibes, and ugly projects. In white-collar work, ideas, intuition and mental
  elasticity need room to convert into success.
- The adjustment is made on the most important asset: the people.

In `team.html`: one light "**first check:** …" line — a suggested default from
project size, freely editable, and explicitly **not** a formula. It is the
stated boundary between what is computed and what is learned by working
together.

## 8b. The source is a public surface too

This is fully OSS: someone reading the repo on GitHub is as much an audience
as someone reading the pages. Everything new must be easy and *pleasant* to
understand from source:

- `pricing.js` reads top-to-bottom like the concept doc: named constants,
  each with a one-line reason and a pointer to its `PRICING.md` section;
  the formula registry is literally the readable list of the N formulas.
- No minification, no cleverness, no build artefacts. Plain HTML/CSS/JS a
  curious freelancer can view-source and follow.
- i18n dictionaries are flat, human-readable files a native speaker can
  correct in a plain PR — that *is* the review gate of §6.
- Comments explain *why* (policy, provenance), not *what* the code does.
- Same bar as the ruleset: if you disagree with a constant, you can find it,
  understand it, and open a PR against it.

## 9. The judge must understand the language — guarantee, not hope

Current state: the LLM judge receives the brief as data with English criteria —
it understands all 8 languages but nothing proves it; `/suggest` already
carries `locale` and writes insertions in the brief's language. The real gap
is the **MockJudge**: English keywords, so the offline console is mute in
other languages.

a. One line added to the judge prompt: *"The brief may be written in any
   language; grade the meaning, not the language; quote evidence verbatim in
   the brief's language."* Explicit instead of implicit.
b. **Multilingual fixtures**: one reference brief translated into all 8
   languages must produce the same gate decision and a score within a declared
   tolerance — run with the real LLM judge, tagged `llm-only` (needs a key,
   outside offline `make test`).
c. The MockJudge **declares its limit** instead of pretending: in a non-EN
   locale the console shows "the offline preview judges English only — the
   real service is multilingual". No false fails.
d. Console example prompts localised (§6) so the real judge is exercised in
   each language.

## 10. Rollout order

1. `pricing.js` extraction + `price.html` port (numeric non-regression)
2. `team.html`
3. `method.html` (narrative + formula blocks + human buffer)
4. Site i18n: switcher + dictionaries — en/it/de/es/ur first, then
   pt-BR/vi/ar
5. Judge multilingual: prompt line + `llm-only` fixtures + console limit note
6. Per-language native-speaker gate before each language ships

Existing Phases 3–4 of `PLAN-PRICING.md` (the €50/h cap decision, CoL
sources, Urdu review, five open decisions, permalink idea) remain valid and
queue after these.

## 11. Testing

- Offline fixtures stay the CI gate (`make test` green throughout).
- Numeric non-regression harness for the `pricing.js` extraction: recorded
  input→output pairs from today's `price.html`.
- Per-language smoke: switch → correct `lang`/`dir`, calculators work, reset
  works, no layout break in RTL.
- `llm-only` multilingual fixture suite (§9b) documented in the Makefile but
  excluded from offline CI.

## 12. Non-goals

- No change to the scoring engine, ruleset, weights, or gate semantics.
- No build step, no external requests from `site/` pages (Lottie CDN pattern
  of `index.html` remains the only existing exception; new pages do not add
  more).
- No individual compensation data, no names: `site/` is public; the
  identified analysis stays in the private cockpit. (Provenance rule of
  `PLAN-PRICING.md` — unchanged.)
- "Team Rate" here is the *equation and page*, not matching/marketplace
  features; the Directory remains the noticeboard.

## 13. Decisions taken in this design (with who took them)

- Brief stays the root; the concept page is `method.html` — Enrico, 2026-07-31
- Team Rate built now, not WIP — Enrico
- One shared engine (`pricing.js`), because the model is a blueprint being
  opened to the world — Enrico
- Whole-site language switch, always visible, 8 languages incl. Spanish
  (kept) — Enrico
- Formulas shown explicitly and counted; human capital stated as what
  augments them — Enrico
- The buffer/check loop, bidirectional — Enrico
