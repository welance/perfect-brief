# Directory branding, ported to perfect-brief

**Date:** 2026-08-09
**Status:** approved, implementing

## The problem

`site/welance.css` says at the top that its tokens came from "welance/Directory
styles.css". They did, once. They have drifted: the accent is violet where the
Directory's is coral, buttons are square where the Directory's are pills, the
container is 1200 where the Directory's is 1320, headings are weight 600 where
the Directory's are 500, and the Directory's clearest signature — the
five-colour rule under the header — was never copied at all. Put the two sites
side by side and they read as cousins, not as one product.

The Directory (`p007-16-welance-website`, served at `/directory/`) is the
reference. Its branding is finished and reviewed. This spec re-syncs
perfect-brief's public pages to it.

Source of truth, by file:

| what | where |
|---|---|
| tokens, type scale, `.btn`, `.badge`, `.sec-label`, nav, footer, closing band | `assets/css/directory/directory.css` |
| header markup + lockup + underline-on-hover | `components/directory/SiteNav.vue` |
| footer markup | `components/directory/Footer.vue` |
| closing band markup | `components/directory/ClosingCTA.vue` |
| the five-colour rule | `layouts/directory.vue` (`.wrule`) |
| logo art | `assets/images/weLogo.svg`, `assets/images/welanceLogo.svg` |

## Decisions taken

1. **Accent: coral.** `--accent` becomes `#ff7b51` everywhere — links, hover,
   section labels, the lead button. Violet survives as `--wl-p`, one of the
   five brand colours, and in the code-block token palette.
2. **Lockup: Directory lockup, underscore kept.** Asterisk + wordmark + grey
   slash + `perfect brief_`.
3. **Dark mode: kept.** The Directory is light-only, but perfect-brief's dark
   theme works and is tested. Directory values become the light palette; the
   dark palette is retuned to match.
4. **Scope: shell + tokens + shared components.** Every page inherits. Bespoke
   per-page CSS in `console.html`, `price.html` and `team.html` is left alone
   except where a token rename would break it.
5. **Footer: the Directory's, wholesale.** Blue closing band on an ink footer.
6. **Chrome additions:** the five-colour rule, the mono status line, and
   underline-on-hover nav links. Not the split pill CTA — the single
   "Find a team" pill stays, re-cut to Directory geometry.

## Invariants this must not touch

Per `CLAUDE.md`: the engine is verified. This is a CSS and chrome-markup
change. `perfect_brief/` is not touched, no number moves, no fixture changes,
no ruleset changes. `site/pricing.js` and `site/splitbar.js` behaviour is
unchanged — `.effortbar`'s *styling* is corrected, not its logic.

## 1. Token layer — `site/welance.css`

### Values re-synced to the Directory

| token | now | becomes |
|---|---|---|
| `--accent` | `#8856cd` | `#ff7b51` |
| `--accent-bg` | `#ede4f8` | `#ffeee8` |
| `--accent-2` | — | `#97dbe2` |
| `--accent-2-fg` | — | `#0a0a0a` |
| `--radius` | — | `999px` |
| `--maxw` | `1200px` | `1320px` |
| `--pad-x` | — | `clamp(16px, 4vw, 56px)` |
| `--muted-2` | — | `#6e6e6e` |
| `--wl-cy` | `#96dbe3` | `#97dbe2` |
| `--wl-b` | — | `#b8c5d6` |
| `--ink-fg` | — | `#f2f2ef` |
| `--ink-muted` | — | `#9a978d` |
| `--ink-line` | — | `#262626` |
| `--verified` | — | `#1d9bf0` |

`--slab` / `--on-slab` / `--on-slab-soft` stay: they are the never-swapping
dark surfaces (CTA band, code block) and predate the Directory's `--ink*` set.
They are re-pointed at the Directory's ink values so the two agree.

### Directory-named aliases

Three rules in the file already reference Directory token names that were never
defined — `.effortbar` uses `--line-strong`, `--surface-2` and `--surface`, so
its border and ground currently resolve to nothing. Rather than rename them,
the Directory's names become first-class aliases on `:root`:

```
--bg: var(--paper);           --fg: var(--ink);
--surface: var(--paper-2);    --surface-2: #efefec;
--line: var(--rule);          --line-strong: var(--rule-strong);
--muted: var(--ink-soft);
--ff-sans: var(--disp);       --ff-mono: var(--mono);
```

This fixes the latent bug and lets Directory CSS be pasted in without a rename
pass. Aliases are redefined inside `[data-theme="dark"]` where the underlying
value swaps.

### Type scale

Ported verbatim from the Directory, replacing the current ad-hoc heading sizes:

- `.h-display` — 500, `clamp(44px, 7vw, 116px)`, `1/0.98`, `-0.028em`
- `.h1` — 500, `clamp(32px, 4.2vw, 60px)`, `1.04`, `-0.022em`
- `.h2` — 500, `clamp(26px, 3vw, 42px)`, `1.08`, `-0.015em`
- `.h3` — 500, `clamp(19px, 1.6vw, 25px)`, `1.2`, `-0.005em`
- `.lead` — `clamp(18px, 1.5vw, 22px)`, `1.45`
- `.eyebrow` / `.mono` — mono, 12px, `0.04em`, uppercase
- `.mono-sm` — mono, 12px, `--muted`, `0.02em`

Bare `h1`–`h3` elements are mapped onto the same values so pages that do not
use the classes still move. Body stays 16px/1.4.

`.sec-label` comes across with its coral `*::before` prefix.

## 2. Header — `site/chrome.js` + `.wl-head*`

### Lockup

`LOGO` (the animated stroke-and-glyph wordmark) is replaced by the Directory's
two static SVGs, inlined: `WE_ASTERISK` (30×30 viewBox) and `WE_WORDMARK`
(112×24 viewBox). The `wl-brandline` two-line block — "an open standard,
started by" over a small mark — is replaced by the Directory's single-line
lockup:

```
[asterisk] [welance] [/] [perfect brief_]
```

- asterisk `22px` → `30px` at ≥1024
- wordmark `85px` → `112px`, `margin-inline-start` `4px` → `8px`
- slash `--muted-2`, label `--ink-soft`, both weight 500, `22px` → `30px`,
  `line-height: 1`, gap `8px`
- the trailing `_` keeps `color: var(--accent)`

The animation (`.wl-logo.animated`, `wl-stroke-draw`, `wl-glyph-in`) becomes
dead code and is removed with it. `chrome.by` becomes an unused i18n key; it is
left in the locale files rather than editing eight of them for nothing.

### Geometry

Header height collapses from three breakpoints (76 / 92 / 100) to the
Directory's two: `76px`, `106px` at ≥1024. Padding `20px` → `48px` at ≥1024
(the Directory's `px-5` / `px-12`). Position stays `sticky` — the Directory's
is `fixed` with a matching body offset, and sticky achieves the same result
without the magic number.

### The five-colour rule

New element, rendered by `chrome.js` as the last child of `.wl-head` so it
sticks with the header:

```css
.wl-rule { display: grid; grid-template-columns: repeat(5, 1fr); height: 3px; }
.wl-rule.is-thin { height: 2px; }
```

Five `<i>` in Directory order: `--wl-c` coral, `--wl-y` yellow, `--wl-cy` blue,
`--wl-p` violet, `--wl-b` steel. `is-thin` on every page except `index.html`,
matching the Directory's home/not-home rule. It replaces the
`border-bottom: 1px solid var(--rule)` on `.wl-head`.

### Nav

`.wl-nav-item` goes to 18px semibold and swaps its colour-change hover for the
Directory's underline: a `::before` bar, `2px`, `bottom: 0.1em`,
`transform: scaleX(0)`, `transition: transform 0.2s ease`, scaling to 1 on
`:hover` and on `[aria-current="page"]`. The existing `box-shadow` current-page
treatment is removed.

### Mono status line

`© 2011–2026 · v1 · live`, mono 11px uppercase `0.06em` in `--ink-soft`, shown
at ≥1280 only, first item in `.wl-head-right`. New key `chrome.status`.

### Pill

`.wl-pill` is re-cut to Directory `.btn` geometry: height 46px, `1px` border
(not 2px), `border-radius: var(--radius)`, 15px weight 500, the standard
invert-on-hover. `.wl-lang-select`, `.wl-theme`, `.wl-src` and `.wl-burger`
take `border-radius: var(--radius)` so nothing square is left in the bar.

## 3. Page close — `site/chrome.js` + `.closing-cta` / `.wl-foot*`

Replaces the black-CTA-band-on-light-footer entirely.

### Closing band

`.closing-cta`: ground `--accent-2` `#97dbe2`, foreground `#0a0a0a`, padding
`clamp(48px, 6vw, 72px) 0`, `position: relative; overflow: hidden`. A 220px
asterisk at `opacity: .18`, `right: -60px; top: -70px`, `aria-hidden`. Inside:
a `sec-label` eyebrow, an `.h1` at `max-width: 18ch`, then two `.btn.lg` — the
lead `.accent` (coral on blue), the second outlined ink. In dark mode the band
keeps its blue ground and ink text: it is a fixed brand surface, like `--slab`.

Copy is the existing footer CTA's: "The team your goal deserves_", with
"Score a brief" and "Find a team →".

### Ink footer

`.wl-foot-deep`: ground `--ink` `#0a0a0a`, foreground `--ink-fg`, padding
`clamp(36px, 5vw, 64px) 0 28px`. Grid `1.4fr 1fr 1fr 1fr`, → `1fr 1fr` at 900,
→ `1fr` at 560.

| column | contents |
|---|---|
| brand | asterisk + wordmark (`--ink-fg`), a 14px `--ink-muted` blurb at `max-width: 34ch`, mono contact line |
| Start here | "Score a brief" / "Compute a split" / "Find a team" as `wl-foot-start` two-line blocks (15px weight-500 title + 12.5px muted sub) |
| The model | `PAGES`, as 14px `wl-foot-link` |
| Build with it | `BUILD`, as 14px `wl-foot-link` |
| Operated by | the two welance offices as `wl-foot-op` 13px muted lines, plus the `welance.com` link |

The GitHub repo link keeps the Directory's open-blue chip: `1px solid var(--wl-cy)`
on `color-mix(in oklab, var(--wl-cy), var(--ink) 82%)`, 5px/10px padding.

Legal bar `.wl-foot-legal`: `border-top` at 18% `--ink-fg`, `margin-top
clamp(28px, 4vw, 44px)`, `padding-top: 16px`, mono `--ink-muted`, flex
space-between wrapping. Language switcher first (it is the only control), then
`© 2011–2026 · MIT`, then Imprint / Privacy / Login and the theme toggle.

Because the footer is now a fixed dark surface in both themes, `.wl-theme`
inside it is restyled against ink rather than paper.

New i18n keys, English literals as fallback until translated:
`chrome.status`, `chrome.slash`, `chrome.blurb`, `chrome.contact`,
`chrome.colStart`, `chrome.colOperated`, `chrome.closingEyebrow`,
`chrome.startBriefSub`, `chrome.startPriceSub`, `chrome.startTeamSub`,
`chrome.privacy`, `chrome.legal`, `chrome.welanceLink`.

## 4. Shared components

- `.btn` — `border-radius: var(--radius)`, height 46 / 36 `sm` / 56 `lg`,
  padding 24 / 16 / 30, weight 500. New `.accent` variant (coral fill, inverts
  to coral-on-transparent). `.primary` and `.ghost` keep their meaning.
- `.badge` — Directory's: mono 11px, `0.07em`, uppercase, `1px solid
  currentColor`, 5/10 padding; `.dot::before` a 6px coral dot.
- `.container` — `max-width: var(--maxw); padding: 0 var(--pad-x)`. Existing
  page wrappers that hardcode `24px` gutters are pointed at `--pad-x`.
- `.hr`, `.grid`, `.grid-2`, `.grid-3`, `.row-between` — added as the Directory
  defines them.
- `.crumbs` / `.wl-crumb` — mono eyebrow spec, coral dot, coral hover.
- `.band` — keeps its `box-shadow` + `clip-path` full-bleed mechanism (the
  Directory has no equivalent and the mechanism is sound and tested). Only its
  colour tokens re-point; `.band.c` is now the accent.
- `.code` — slab treatment kept. `.code .n` and `.code .k` re-point at
  `--wl-p` / `--wl-cy`; the yellow underline on `[aria-pressed="true"]` becomes
  coral so the active tab agrees with the rest of the site.
- `.effortbar` — resolves `--line-strong`, `--surface`, `--surface-2` for the
  first time via the aliases. Grip accent follows coral.

## 5. Verification

1. `make test` — fixtures + API, mock judge. Must stay green; nothing it covers
   is touched.
2. `make test-site` — the pricing engine. Same.
3. `tests/e2e/site.spec.mjs` asserts on chrome and will need updating for the
   new lockup, nav and footer. `tests/e2e/console-score-button.spec.mjs`
   (untracked) is checked for the same.
4. Every page — `index`, `console`, `rules`, `method`, `price`, `team`,
   `calculators`, `data`, `integrate`, `security` — at 375 / 768 / 1440, in
   both themes:
   - no horizontal scrollbar (`scrollWidth <= clientWidth`);
   - the header holds without overflow;
   - the brand rule is 3px on `index` and 2px elsewhere;
   - text on the blue band and the ink footer clears AA.
5. Side-by-side screenshots of `localhost:3000/directory/` and
   `localhost:8000/` at 1440.

## Out of scope

- Per-page layout rework (the Directory's hero grid, card patterns, stat rows).
  The console and price UIs are verified; this spec does not restructure them.
- The split pill CTA.
- Translating the new i18n keys — they fall back to English, consistent with
  the draft-badge treatment the site already uses.
- Serving Maison Neue locally. perfect-brief loads it from welance.com over
  CORS and that keeps working.
