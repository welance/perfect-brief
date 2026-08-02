# The Welance Method Digitalised — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish Perfect Price properly, build Perfect Team (the missing
equation) and the method.html narrative page, and make the whole site speak
8 languages — per the approved spec
`docs/superpowers/specs/2026-07-31-perfect-method-price-team-design.md`.

**Architecture:** One shared, dependency-free engine (`site/pricing.js`) owns
all pricing policy/math and the formula registry; `price.html` and `team.html`
are thin UIs over it. `site/i18n.js` + per-language dictionaries own every
string on every page. The brief engine (`perfect_brief/`) is untouched except
one prompt line and new llm-only fixtures.

**Tech Stack:** Plain HTML/CSS/JS, no build step, no external requests.
`node --test` for engine tests (dev-only; offline CI stays `make test`).

## Global Constraints

- `site/` is public and fully anonymised: **no names, no individual
  compensation data, ever** (PLAN-PERFECT-PRICE.md provenance rule).
- **No build step, no external requests** from site pages (existing Lottie
  CDN in index.html is the only grandfathered exception).
- **Surgical edits only** to `index.html` and `console.html` — never rewrite.
- The source is a public surface (spec §8b): named constants with a one-line
  reason + pointer to `docs/perfect-price/PERFECT-PRICE.md` section; comments
  explain *why*, not *what*; no minification, no cleverness.
- Voice (CLAUDE.md): modest but professional, sincere, no hype words.
  `site/index.html` is the reference.
- `make test` (offline fixtures) must stay green after every task.
- Numeric truth: LEVELS share 0.70/0.60/0.50 ↔ margin 0.30/0.40/0.50;
  coverage thresholds 0.875/0.625; `agreed()` rounds toward the person
  (0.75→1, 0.25→0.5); CoL `max(coef, floor)`; internal cap €50/h.
  These come from `site/price.html` today and MUST NOT drift.
- Languages: `en` (default) · `de` · `it` · `ur` (RTL) · `pt-BR` · `vi` ·
  `ar` (RTL) · `es`. New translations are machine-drafted and carry
  `reviewed: false` until a native speaker approves (UI shows a draft badge).

---

### Task 1: `site/pricing.js` — the shared engine + formula registry

**Files:**
- Create: `site/pricing.js`
- Test: `tests/site/pricing.test.mjs`
- Modify: `Makefile` (add `test-site` target)

**Interfaces:**
- Consumes: nothing (pure, zero-dep, no DOM).
- Produces (global `WelancePricing` via plain script tag, and the same object
  via `module.exports` when `typeof module !== "undefined"` so node can test
  it):
  - `LEVELS`: `[{id:"autonomous",cover:1.00,share:0.70},
    {id:"with-review",cover:0.75,share:0.60},
    {id:"with-support",cover:0.50,share:0.50}]`
  - `STEPS = [1, 0.5, 0]`, `INTERNAL_MAX = 50`
  - `COUNTRIES`: the 12-entry table copied verbatim from `price.html`
    (lines ~588–602), coefficients unchanged
  - `agreed(c)`, `coverageOf(list)`, `levelFor(cov)` — moved verbatim from
    `price.html` (lines ~729–744)
  - `share(cov)` → `0.30 + 0.40 * cov`
  - `applyCol(payout, coef, floor)` → `payout * Math.max(coef>0?coef:1, floor>0?floor:0)`
  - `minClientRate(payout, marginTarget)` → `payout / (1 - marginTarget)`
  - `computeTeam(R, rows)` — rows:
    `[{weight, levelIndex, coef, floor, ownRate}]` (weights normalised over
    their sum). Returns:
    ```js
    {
      rows: [{ ceiling,            // R * share_i * col_i  (local ceiling)
               roleOnlyCeiling,    // R * share_i          (before CoL)
               ok,                 // ownRate <= ceiling  (no-deal per row)
               headroom }],        // ceiling - ownRate (>=0 when ok)
      payouts,      // Σ w_i * ownRate_i          (€/h blended, to the people)
      headroom,     // Σ w_i * (ceiling_i - ownRate_i)
      geoBand,      // Σ w_i * share_i * (1 - col_i) * R   (the CoL differential)
      welanceMargin,// Σ w_i * m(level_i) * R              (the named recipe)
      marginTarget, // Σ w_i * m(level_i)                  (rate-free, 0..1)
      ok,           // every row ok
      minViableR    // max_i( ownRate_i / (share_i * col_i) )
    }
    ```
    Identity that must hold: `payouts + headroom + geoBand + welanceMargin === R`.
  - `FORMULAS`: array of 8 entries
    `{id, n, name, formula, plain, source}` — ids:
    `score`, `gate`, `coverage`, `share`, `margin`, `col`, `nodeal`, `team`;
    `formula` is the human-readable one-liner (e.g.
    `"share = 30% + 0.4 × coverage"`), `plain` one sentence, `source` the
    doc section (e.g. `"PERFECT-PRICE.md §3"`; score/gate point at
    `perfect_brief/scoring.yaml`). `n` = 1-based index;
    **pages must derive the count from `FORMULAS.length`, never hardcode 8.**

- [ ] **Step 1: Write the failing test**

`tests/site/pricing.test.mjs`:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const P = require("../../site/pricing.js");

test("levels sample the share line", () => {
  for (const lv of P.LEVELS)
    assert.equal(Number(P.share(lv.cover).toFixed(2)), lv.share);
});

test("agreed rounds toward the person", () => {
  assert.equal(P.agreed({ self: 1, evalr: 0.5 }), 1);     // 0.75 → 1
  assert.equal(P.agreed({ self: 0.5, evalr: 0 }), 0.5);   // 0.25 → 0.5
  assert.equal(P.agreed({ self: 1, evalr: 1 }), 1);
});

test("coverage thresholds pick the level", () => {
  assert.equal(P.levelFor(0.875).id, "autonomous");
  assert.equal(P.levelFor(0.874).id, "with-review");
  assert.equal(P.levelFor(0.625).id, "with-review");
  assert.equal(P.levelFor(0.624).id, "with-support");
});

test("CoL floor binds", () => {
  assert.equal(P.applyCol(100, 0.28, 0.4), 40);
  assert.equal(P.applyCol(100, 0.82, 0.4), 82);
});

test("no-deal minimum client rate", () => {
  assert.equal(P.minClientRate(59.5, 0.3), 85); // worked example, concept §9
});

// The team equation — pinned numbers, computed by hand in the plan.
const rows = [
  { weight: 0.30, levelIndex: 0, coef: 1.00, floor: 0, ownRate: 55 },
  { weight: 0.45, levelIndex: 1, coef: 0.82, floor: 0, ownRate: 40 },
  { weight: 0.25, levelIndex: 2, coef: 0.32, floor: 0, ownRate: 12 },
];
test("computeTeam decomposes R into four bands", () => {
  const r = P.computeTeam(100, rows);
  assert.equal(r.ok, true);
  assert.equal(Number(r.payouts.toFixed(2)), 37.5);
  assert.equal(Number(r.headroom.toFixed(2)), 9.64);
  assert.equal(Number(r.geoBand.toFixed(2)), 13.36);
  assert.equal(Number(r.welanceMargin.toFixed(2)), 39.5);
  assert.equal(Number(r.marginTarget.toFixed(3)), 0.395);
  const total = r.payouts + r.headroom + r.geoBand + r.welanceMargin;
  assert.ok(Math.abs(total - 100) < 1e-9);
  assert.equal(Number(r.minViableR.toFixed(2)), 81.30);
});

test("computeTeam flags the failing row, never compresses", () => {
  const r = P.computeTeam(70, rows); // fullstack ceiling 70*0.6*0.82=34.44 < 40
  assert.equal(r.ok, false);
  assert.equal(r.rows[1].ok, false);
});

test("formula registry is the count", () => {
  assert.equal(P.FORMULAS.length, 8);
  assert.deepEqual(P.FORMULAS.map(f => f.n), [1,2,3,4,5,6,7,8]);
  for (const f of P.FORMULAS)
    for (const k of ["id","name","formula","plain","source"])
      assert.ok(f[k], `${f.id ?? "?"} missing ${k}`);
});
```

- [ ] **Step 2: Run it, confirm it fails**

Run: `node --test tests/site/pricing.test.mjs`
Expected: FAIL — `Cannot find module '../../site/pricing.js'`

- [ ] **Step 3: Write `site/pricing.js`**

Structure (readable top-to-bottom like the concept doc — spec §8b):

```js
/* Welance pricing — the whole model in one readable file.
 * Every constant has a reason, recorded in docs/perfect-price/PERFECT-PRICE.md;
 * the section is cited next to each. If you disagree with a number: find it,
 * read its section, open a PR against it. That is the point of this file.
 * No DOM, no dependencies. price.html and team.html are UIs over this. */
(function (root) {
  "use strict";

  // §3 The rule — the three levels are one line, sampled.
  var LEVELS = [
    { id: "autonomous",   cover: 1.00, share: 0.70 },
    { id: "with-review",  cover: 0.75, share: 0.60 },
    { id: "with-support", cover: 0.50, share: 0.50 }
  ];
  function share(cov) { return 0.30 + 0.40 * cov; }        // §3
  function marginOf(levelIndex) { return 1 - LEVELS[levelIndex].share; } // §3

  var STEPS = [1, 0.5, 0];                                  // §4 full/partial/none
  var INTERNAL_MAX = 50;   // §6 internal work has no client rate (Enrico 2026-07-31)

  // §7 Cost of living — EDITABLE DEFAULTS ONLY, replace from OECD PPP /
  // World Bank ICP / Numbeo before anyone is paid from them.
  var COUNTRIES = [ /* copied verbatim from price.html, 12 entries */ ];

  function agreed(c) { /* verbatim from price.html: mean, round toward person */ }
  function coverageOf(list) { /* verbatim: weighted mean of agreed() */ }
  function levelFor(cov) { return cov >= 0.875 ? LEVELS[0] : cov >= 0.625 ? LEVELS[1] : LEVELS[2]; }
  function applyCol(payout, coef, floor) { /* §7: payout × max(coef, floor) */ }
  function minClientRate(payout, marginTarget) { return payout / (1 - marginTarget); } // §8 no-deal

  function computeTeam(R, rows) { /* as specified in Interfaces above */ }

  // The N formulas. Pages derive N from FORMULAS.length — never hardcode it.
  var FORMULAS = [
    { id: "score",    n: 1, name: "The score",        formula: "score = Σ weightᵢ × verdictᵢ  (weights sum to 100)", plain: "How good a brief is: a weighted average over public, versioned rules.", source: "perfect_brief/scoring.yaml" },
    { id: "gate",     n: 2, name: "The gate",         formula: "publish ⇔ every hard requirement holds",             plain: "Whether a brief may publish at all — no average can paper over a hard miss.", source: "perfect_brief/scoring.yaml" },
    { id: "coverage", n: 3, name: "Coverage",         formula: "coverage = Σ wᵢ × agreedᵢ / Σ wᵢ",                   plain: "How much of a role someone covers, part by part, agreed by both views.", source: "PERFECT-PRICE.md §4" },
    { id: "share",    n: 4, name: "The share",        formula: "share = 30% + 0.4 × coverage",                       plain: "The slice of the client rate that goes to the person — it follows from coverage, nothing else.", source: "PERFECT-PRICE.md §3" },
    { id: "margin",   n: 5, name: "The margin rule",  formula: "(R − payout) / R ≥ m(level)",                        plain: "What the collective retains, priced as the risk it actually carries at that level.", source: "PERFECT-PRICE.md §3" },
    { id: "col",      n: 6, name: "Cost of living",   formula: "payout_local = payout_role × max(coeff, floor)",     plain: "A stated, floored geographic adjustment — always shown as its own band, never hidden in margin.", source: "PERFECT-PRICE.md §7" },
    { id: "nodeal",   n: 7, name: "No-deal",          formula: "client < payout/(1−m) → the engagement does not happen", plain: "Nobody is squeezed below their own rate to make a margin work.", source: "PERFECT-PRICE.md §8" },
    { id: "team",     n: 8, name: "The team equation",formula: "R = payouts + headroom + geo differential + welance margin", plain: "One blended client rate, decomposed into four visible bands that must sum exactly.", source: "spec §5" }
  ];

  var API = { LEVELS, STEPS, INTERNAL_MAX, COUNTRIES, share, marginOf,
              agreed, coverageOf, levelFor, applyCol, minClientRate,
              computeTeam, FORMULAS };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  root.WelancePricing = API;
})(typeof self !== "undefined" ? self : globalThis);
```

Write each `plain` as one real sentence in the site voice (no hype). The
`/* verbatim */` markers mean: move the function bodies from
`site/price.html` lines 729–752 unchanged.

- [ ] **Step 4: Run the tests, confirm all pass**

Run: `node --test tests/site/pricing.test.mjs`
Expected: PASS (all)

- [ ] **Step 5: Add the Makefile target and run it**

```makefile
test-site: ## engine tests for site/pricing.js (dev-only, needs node)
	node --test tests/site/pricing.test.mjs
```

Run: `make test-site` → PASS. Run `make test` → still green (untouched).

- [ ] **Step 6: Commit**

```bash
git add site/pricing.js tests/site/pricing.test.mjs Makefile
git commit -m "site: pricing.js — one shared engine and the formula registry"
```

---

### Task 2: Port `price.html` onto `welance.css` + the shared engine

**Files:**
- Modify: `site/price.html` (styles lines 2–221; script lines 333–1081)

**Interfaces:**
- Consumes: `WelancePricing` from Task 1 (`<script src="pricing.js?v=1">`).
- Produces: unchanged page behaviour; its private `T`/i18n stays for now
  (Task 6 migrates it).

- [ ] **Step 1: Record today's numbers (the non-regression oracle)**

Open `site/price.html` in a browser. Write down, in a scratch note, the
displayed share/margin/payout for: (a) untouched defaults (client work:
coverage 50% → WITH SUPPORT → share 50%, €50/h on €100/h), (b) all parts
Full (→ AUTONOMOUS 70%), (c) CoL on, Pakistan 0.28 floor 0.40 (floor binds),
(d) internal work (cap €50). These four are re-checked in Step 4.

- [ ] **Step 2: Swap the engine**

Add `<script src="pricing.js?v=1"></script>` before the inline script.
Inside the inline script delete the local `COUNTRIES`, `LEVELS`, `STEPS`,
`INTERNAL_MAX` declarations and the `agreed`, `coverageOf`, `levelFor`
function bodies; replace with:

```js
var P = window.WelancePricing;
var COUNTRIES = P.COUNTRIES, LEVELS = P.LEVELS, STEPS = P.STEPS,
    INTERNAL_MAX = P.INTERNAL_MAX;
var agreed = P.agreed, coverageOf = P.coverageOf, levelFor = P.levelFor;
```

Keep `geoCoef()` (it reads the DOM) but make its last line
`return P.applyCol(1, c, floor);`-equivalent — i.e. delegate the max() to
`P.applyCol`. Everything else in the script stays.

- [ ] **Step 3: Restyle onto `welance.css`**

Head: add `<link rel="stylesheet" href="welance.css?v=3">` before the inline
`<style>`. In the inline style: delete the local token definitions
(`--bg --ink --serif --mono` blocks, both themes) and map usages onto the
site tokens (`--paper --paper-2 --ink --ink-soft --rule --accent --mono
--disp --maxw`) exactly as `console.html` does (open it side by side; it is
the precedent for a tool page on the shared sheet). KEEP the component
styles the sheet has no equivalent for: the split bar, the coverage ladder,
the parts grid, `.rowflag`, `.fig` panel. Replace the page header with the
breadcrumb header pattern from `rules.html` (logo svg + `welance /
perfect price`), copied verbatim and retitled.

- [ ] **Step 4: Verify zero numeric regression + behaviours**

Re-run the four oracle checks from Step 1 — identical numbers.
Then: switch all 5 languages (Urdu flips `dir=rtl`), toggle themes, edit a
part → reload (dirty set survives), press reset (defaults return), switch
work type both ways. `make test-site && make test` → green.

- [ ] **Step 5: Commit**

```bash
git add site/price.html
git commit -m "site: price.html on welance.css and the shared engine — no numeric change"
```

---

### Task 3: `team.html` — the missing equation

**Files:**
- Create: `site/team.html`
- Test: browser checklist below + engine already covered by Task 1 tests

**Interfaces:**
- Consumes: `WelancePricing.computeTeam`, `.LEVELS`, `.COUNTRIES`,
  `.FORMULAS`, `welance.css`, breadcrumb pattern from `rules.html`.
- Produces: the page Task 4 links as step 3 and Task 6 internationalises.

- [ ] **Step 1: Build the page**

Same metaphor as price.html — the "name" is the team's name, the parts are
roles. Structure (all styling via `welance.css` + the component styles
ported in Task 2, breadcrumb `welance / perfect team`):

- Header: title "One team, one rate" (`<h1>Perfect Team<span class="b">_</span></h1>`
  pattern), lede: the client sees one blended rate, not a hundred; margins
  vary inside the team; the project clears the welance margin — stated,
  named, checkable.
- Team card: team name input (default `"Team — product rebuild"`, anonymised),
  role rows. Per row: role name · weight % · level `<select>` (3 levels) ·
  country `<select>` from `COUNTRIES` + editable coefficient + floor ·
  member's own rate €/h. Default rows = the three from the plan's pinned
  test (design lead / full-stack dev / QA with those exact numbers), role
  names only, no people.
- Client rate input `R` (default 100) + a computed line
  "minimum viable R: €…" from `minViableR`.
- The split bar: **four bands, four colours** — to the people · headroom ·
  geographic differential · welance margin. The geo band keeps its own
  colour from price.html; headroom gets its own; neither is ever merged
  into margin (spec §5a — the identity `payouts + headroom + geoBand +
  welanceMargin = R` is literally the bar).
- Per-row no-deal flag: when `!row.ok`, the row shows
  "At €R the ceiling for this role is €X — below their €Y. Either R rises,
  or this team does not happen." Nobody is compressed (spec §5b).
- Result figures: blended payout €/h, welance margin % vs weighted target %
  (they coincide at ceilings; actual margin grows with headroom — show both
  numbers side by side).
- "First check" line (spec §8): `first check: <select>` with suggested
  defaults 3 days / 2 weeks / 1 month by project size S/M/L, freely
  editable, and the sentence: "A suggested rhythm, deliberately not a
  formula: what the formulas cannot see — compatibility, kindness,
  stress, soft skills — is learned only by working together, and the check
  is where either side may say so."
- Every computed figure gets `title="formula N of {FORMULAS.length}: …"`
  tooltips derived from `FORMULAS` (share→4, margin→5, col→6, nodeal→7,
  team→8).
- State in `localStorage` under `welance-team-calc-v1` (same dirty-tracking
  pattern as price.html: defaults until first edit, then the user's), reset
  button restores defaults.
- Footer: the CoL destination note (f1) and no-deal note (f2) texts reused
  from price.html's English footer, plus one line: "Coefficients are
  editable defaults and need a real source before anyone is paid from them."

JS shape — keep it small and readable; all math through the engine:

```js
var P = window.WelancePricing;
function currentRows() { /* read the DOM rows into computeTeam input */ }
function render() {
  var R = Number($("clientRate").value) || 0;
  var r = P.computeTeam(R, currentRows());
  // bar widths in % of R: r.payouts, r.headroom, r.geoBand, r.welanceMargin
  // figures, per-row flags from r.rows[i].ok, minViableR line
}
```

- [ ] **Step 2: Verify against the pinned numbers**

With the default rows and R=100 the page must show: to the people €37.50/h ·
headroom €9.64 · geo differential €13.36 · welance margin €39.50 (39.5%,
target 39.5%) · minimum viable R €81.30. Set R=70 → the full-stack row
flags no-deal and the verdict line appears. Reset works; reload keeps edits;
both themes hold; the bar always sums to the full width.

- [ ] **Step 3: Commit**

```bash
git add site/team.html
git commit -m "site: team.html — one blended rate, four visible bands, no-deal per row"
```

---

### Task 4: `method.html` — the narrative page

**Files:**
- Create: `site/method.html`

**Interfaces:**
- Consumes: `welance.css`, breadcrumb pattern, `WelancePricing.FORMULAS`
  (for the formula blocks and the derived count).
- Produces: the page Task 5 links from index nav/footer.

- [ ] **Step 1: Write the page**

Voice of `index.html`, structure of `rules.html` (eyebrow sections). Copy —
write it out fully in the page, English (Task 6 adds languages), along these
beats, in this order:

1. **The problem** (eyebrow: "the problem, honestly"): a rigid business unit
   cannot change shape for a specific goal; it adapts itself, rigidly, and
   the result is worse and the budget wasted. Welance experiences and solves
   this as consultants — it is the generalist problem behind every other one.
   A cross-functional team assembled *for* the goal — personally and
   professionally inclined to it, not adapted to it — does better work.
2. **The three steps** (eyebrow: "the method — three steps"): three cards in
   causal order, each with a stroke-draw ident (same technique as
   index.html's `.pb-ident`, ~6 strokes each) and a link:
   — **1 · Perfect Brief** → `index.html` — what the work is. The 20% that
   decides whether a good team can start well.
   — **2 · Perfect Price** → `price.html` — what it is worth and who gets
   what part, stated so anyone can compute and check the split.
   — **3 · Perfect Team** → `team.html` — who does it, where in the world,
   at one blended rate the client can actually reason about.
   Each step needs the one before: the price needs the brief's scope; the
   team needs the price's arithmetic. That cascade is the method.
3. **The formulas** (eyebrow: "the formulas, all of them"): render every
   entry of `FORMULAS` as a visual block (`.formula` style ported from
   price.html: name, the formula line in mono, the plain sentence, source).
   Heading text derives the count: `"The " + FORMULAS.length + " formulas"`.
   Closing line, verbatim intent: *"These N formulas help make the decision.
   Everything else is human capital — and it does not compute."*
4. **Si parte! — the human buffer** (eyebrow: "what the formulas cannot
   see"): the formulas produce the *starting* team. Cultural compatibility —
   between members, and with the client — kindness, humanity, availability,
   how someone carries stress: none of it computes; it is learned only by
   collaborating. So work starts for real, with scheduled checks at 1–2–3
   days, weeks or months depending on the project's size and complexity,
   and the declared reserve to replace, remove or modify the initial
   choices. Always bidirectional: the independent may not feel right
   either, and every human problem must surface fast — that is what
   prevents resentment, bad vibes and ugly projects. In white-collar work,
   ideas, intuition and mental elasticity need room to convert into
   success. The adjustment is made on the most important asset: the people.
5. **The blueprint** (eyebrow: "why open"): this is the process Welance has
   run in person since 2012 — take an honest brief, price it transparently,
   assemble the team around it — digitalised end to end and opened as a
   blueprint. MIT like the rest; if you disagree with a constant, it is in
   one readable file, and you can fork the whole method.
- Footer: same pattern as the other pages, links to all three steps +
  github.

- [ ] **Step 2: Verify**

Read it against CLAUDE.md's tone section — no hype words. Both themes.
The formulas section shows exactly `FORMULAS.length` blocks. All five links
resolve. Reduced-motion disables the stroke-draw animations
(`prefers-reduced-motion` pattern from index.html).

- [ ] **Step 3: Commit**

```bash
git add site/method.html
git commit -m "site: method.html — the welance method as three steps, N formulas, and the human buffer"
```

---

### Task 5: Surgical edits to `index.html`

**Files:**
- Modify: `site/index.html:100-104` (the `.cta` block) and `:147-150`
  (footer)

**Interfaces:**
- Consumes: `method.html` from Task 4.
- Produces: discoverability; the switcher mount comes in Task 6.

- [ ] **Step 1: Add the two links**

In `.cta` (after the "Read the rules" anchor):
`<a class="btn ghost" href="method.html">The method</a>`
In the footer span: add `<a href="method.html">method</a> · ` before the
console link. Nothing else changes.

- [ ] **Step 2: Verify + commit**

Open the page, both links work, layout intact at 560px and 1200px.

```bash
git add site/index.html
git commit -m "site: index links the method page — surgical"
```

---

### Task 6: Site-wide i18n — `i18n.js`, dictionaries, the always-present switcher

**Files:**
- Create: `site/i18n.js`, `site/i18n/en.js`, `site/i18n/de.js`,
  `site/i18n/it.js`, `site/i18n/ur.js`, `site/i18n/pt-BR.js`,
  `site/i18n/vi.js`, `site/i18n/ar.js`, `site/i18n/es.js`
- Modify: `site/index.html`, `site/method.html`, `site/team.html`,
  `site/rules.html`, `site/console.html`, `site/price.html`

**Interfaces:**
- Consumes: every page's header; price.html's existing `T` dict (source of
  the 5 existing translations).
- Produces: `WelanceI18n = { lang, dir, t(key), set(lang), LANGS }`;
  dictionaries as `WelanceI18n.register("de", { reviewed: true, strings: {…} })`.

- [ ] **Step 1: Build `site/i18n.js`**

Plain script, no deps. Responsibilities, in ~120 readable lines:
- `LANGS` = the 8 codes with native names and `dir`
  (`ur` and `ar` are `rtl`); `en` is the fallback and lives in the markup.
- Resolution order: `?lang=` param → `localStorage["welance-lang"]` → `en`.
- `set(lang)`: stores, sets `document.documentElement` `lang` + `dir`,
  walks `[data-i18n]` nodes (`textContent` by default,
  `data-i18n-html` opts into `innerHTML` for the few strings with markup,
  `data-i18n-attr="placeholder|title"` for attributes), missing key →
  leave English and `console.warn` once.
- Renders the switcher into `<nav id="langswitch">`: one button per
  language, `aria-pressed` on the active one, and a small `draft` badge
  (mono, `--ink-soft`) when the dictionary has `reviewed: false`.
- Dictionaries are separate files so a native speaker can correct one in a
  plain PR — flat `key: "string"` objects, keys namespaced
  `site.* index.* method.* team.* price.* console.* rules.*`.

- [ ] **Step 2: Mount the switcher on every page**

Each page header (next to the breadcrumb, all six pages) gets:

```html
<nav id="langswitch" aria-label="language"></nav>
<script src="i18n.js?v=1"></script>
<script src="i18n/en.js"></script> …one tag per language…
```

Surgical placement: inside the existing header flex containers; on
`index.html` inside `.head-grid .txt` after the crumbs.

- [ ] **Step 3: Extract and draft the dictionaries**

- `en.js`: key every user-facing string of all six pages (`data-i18n`
  attributes added page by page; English text stays in the markup as the
  content of record).
- `de/it/ur/pt-BR`: seed `price.*` keys from price.html's existing `T`
  (verbatim — these are already good), mark `reviewed: true` for the
  migrated price strings' languages only if they were already shipped
  (they were: keep `reviewed: true` for de/it/pt-BR, `false` for ur — the
  Urdu native review from PLAN-PERFECT-PRICE.md Phase 4 is still owed);
  machine-draft the rest of the site's keys; overall file flag
  `reviewed: false` until a native speaker passes over the whole file.
- `vi.js`, `ar.js`, `es.js`: machine-draft everything, `reviewed: false`.
  `ar` is Modern Standard Arabic; review is owned by Palestinian native
  speakers (spec §6).
- Include the **console example briefs** as `console.example.*` keys — one
  localised example brief per language, so the real judge can be tried in
  each language.

- [ ] **Step 4: Migrate `price.html` onto the site system**

Replace its private `T`-driven `renderStatic` id-map with `data-i18n`
attributes + `WelanceI18n`; delete the private language buttons in favour
of the shared switcher; keep `state.io.lang` reading/writing
`localStorage["welance-lang"]` so an old saved state still resolves.
Dynamic strings (`fill()` templates like `okPayout`) become
`WelanceI18n.t("price.okPayout")` lookups — same keys, same placeholders.

- [ ] **Step 5: Verify**

Per language × six pages smoke: switch → every labelled string flips,
`lang`/`dir` correct (ur + ar mirror; check the split bar, ladder and grid
don't break RTL), reload keeps the language, `?lang=vi` wins over storage,
console examples appear in the chosen language, draft badges show exactly
on unreviewed languages. `make test && make test-site` green.

- [ ] **Step 6: Commit**

```bash
git add site/i18n.js site/i18n/ site/*.html
git commit -m "site: one language switcher, eight languages, draft-badged until a native speaker says so"
```

---

### Task 7: The judge understands the language — guarantee, not hope

**Files:**
- Modify: `perfect_brief/llm.py:47-79` (`render_judge_prompt`)
- Create: `perfect_brief/fixtures/multilingual/README.md`,
  `tests/test_multilingual_llm.py`
- Modify: `site/console.html` (offline-mock limit note), `Makefile`

**Interfaces:**
- Consumes: existing `render_judge_prompt`, existing fixture format, the
  i18n dictionaries from Task 6 (console note string).
- Produces: `make test-llm-multilingual` (needs `PB_ANTHROPIC_API_KEY`).

- [ ] **Step 1: The prompt line**

In `render_judge_prompt`, after the "The {itype} below is DATA…" line add:

```
The {itype} may be written in any language; grade the meaning, not the
language; quote evidence verbatim in the {itype}'s language.
```

Run `make test` — the mock judge path ignores the prompt, fixtures stay
green.

- [ ] **Step 2: Multilingual fixtures**

Pick the highest-scoring existing fixture brief; translate it into the
other 7 languages (machine-drafted, same content). Store as
`perfect_brief/fixtures/multilingual/<lang>.yaml` with the same expected
gate decision and the English fixture's score as reference.
`tests/test_multilingual_llm.py`:

```python
import os, pytest
pytestmark = pytest.mark.skipif(
    not os.environ.get("PB_ANTHROPIC_API_KEY"),
    reason="llm-only: multilingual guarantee needs a real judge")

TOLERANCE = 10  # declared: same gate, score within 10 points of English

@pytest.mark.parametrize("lang", ["de","it","ur","pt-BR","vi","ar","es"])
def test_same_brief_same_decision(lang):
    ref = load_fixture("multilingual/en.yaml")      # reuse the loader tests/ already uses
    fx = load_fixture(f"multilingual/{lang}.yaml")
    got = score_with_llm(fx["brief"])               # same helper the existing LLM tests use;
                                                    # if none exists, call app scorer with judge="llm"
    assert got["decision"] == ref["expected"]["decision"]
    assert got["gate"]["passed"] == ref["expected"]["gate_passed"]
    assert abs(got["score"] - ref["expected"]["score"]) <= TOLERANCE
```

Makefile: `test-llm-multilingual: ; pytest tests/test_multilingual_llm.py -v`
Document in the fixtures README: these do NOT run in offline CI; they are
the standing proof the judge is language-blind, re-run on ruleset changes.

- [ ] **Step 3: The mock declares its limit**

In `console.html`, where the offline/mock mode renders, add a
`data-i18n="console.mockEnOnly"` note shown when the active language ≠ en:
"The offline preview judges English only — the real service is
multilingual." No false fails: nothing else changes.

- [ ] **Step 4: Run what can run, commit**

`make test` green; `make test-llm-multilingual` runs (or cleanly skips
without a key).

```bash
git add perfect_brief/llm.py perfect_brief/fixtures/multilingual tests/test_multilingual_llm.py site/console.html Makefile
git commit -m "judge: multilingual as a guarantee — prompt line, llm-only fixtures, honest mock"
```

---

### Task 8: Supersede the old plan, update CLAUDE.md

**Files:**
- Modify: `PLAN-PERFECT-PRICE.md` (top note), `CLAUDE.md` (workstream para)

- [ ] **Step 1: Point the old plan here**

At the top of `PLAN-PERFECT-PRICE.md`, under the title:

```markdown
> **Superseded 2026-07-31** by
> `docs/superpowers/plans/2026-07-31-perfect-method-price-team.md`
> (spec: `docs/superpowers/specs/2026-07-31-perfect-method-price-team-design.md`).
> Phases 3–4 below (the €50/h cap decision, CoL sources, Urdu review, the
> five open decisions, the permalink idea) are still owed and queue after it.
```

- [ ] **Step 2: CLAUDE.md**

In the "Second workstream" paragraph: replace the sentence
"calculator in `site/price.html` (working, not yet on `welance.css`)" with
"engine in `site/pricing.js` (shared by `price.html` and `team.html`),
narrative in `site/method.html`, site-wide i18n in `site/i18n.js` — plan in
`docs/superpowers/plans/2026-07-31-perfect-method-price-team.md`."

- [ ] **Step 3: Commit**

```bash
git add PLAN-PERFECT-PRICE.md CLAUDE.md
git commit -m "docs: perfect-price plan superseded by the method plan"
```

---

## Deferred (recorded, not in this plan)

- Per-language native-speaker review sessions (the publication gate that
  flips `reviewed: true`) — human work, scheduled with the collective.
- PLAN-PERFECT-PRICE.md Phases 3–4 decisions (€50/h cap publication, CoL
  real sources, five open decisions, URL-hash permalink).
- welance.com navigation pointing at the method page.
