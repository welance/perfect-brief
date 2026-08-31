# The phone layer — design

**Date:** 2026-08-28
**Status:** implemented — OK for now (2026-08-31)
**Scope:** `site/` only. No engine, no API, no ruleset.

**Final interaction amendment.** Testing the implemented calculator sheet
showed that it preserved too much information and competed with the header.
The shipped price/team pattern is therefore one focused Edit/Answer workspace:
one input card at a time, the existing result panel as the Answer view, and one
fixed live footer containing the amount, compressed split and percentage or
margin. The draggable sheet described below remains the console pattern and
the historical rationale for the first implementation; the shared mobile
fundamentals, swipe action and installability decisions remain unchanged.

## 1. The problem, stated precisely

On a phone the site has one defect that matters more than every other one
combined: **the answer leaves the screen.**

`price.html` and `team.html` put their result in a second column
(`.cols` → `.sticky`). Under 920px that column collapses:

```css
@media (max-width: 920px) { .cols { grid-template-columns: 1fr } }
@media (max-width: 920px) { .sticky { position: static } }
```

The result panel — the split bar, the four figures, the formula, the verdict —
falls to the bottom of a long stack of input cards. You drag a weight and then
scroll to find out what it did. A calculator whose output is off-screen while
you type is not a calculator; it is a form.

`console.html` already found the answer for itself. Under 900px `.vstick`
becomes `position: fixed; bottom: 0`, a `.vhandle` button toggles a
`.collapsed` class, and `body` gets `padding-bottom: 190px` so the page does
not end underneath it. That is a bottom sheet without the gesture.

Alongside it, five findings from the audit, each a known mobile failure:

| Finding | Consequence |
|---|---|
| No `inputmode` on any of the six number fields | Wrong keyboard, extra taps per value |
| Input `font-size` 13.5–15px | **iOS zooms the page on every focus** and does not zoom back |
| No `viewport-fit=cover` | Safe-area insets unavailable; a fixed bar sits under the home indicator |
| No `dvh` units | `100vh` overflows behind mobile browser chrome |
| No manifest | No installable/standalone mode at all |

`splitbar.js` is *not* on this list. It already uses pointer capture,
`touch-action: none`, keyboard control and RTL mirroring. It is the foundation
to build on, not something to replace.

## 2. Principles

1. **Generalise the console's answer; do not add a second one.** One sheet
   behaviour, three tools. The console keeps its handle, its `.collapsed`
   styling and its passing tests, and gains the gesture.
2. **The DOM does not change.** The panel each page already has becomes the
   sheet in place — same nodes, same listeners, same i18n keys, same tests.
   Duplicate mobile markup would fork every translation and is rejected
   outright.
3. **Progressive.** The layer turns on only when JS runs *and* the device is
   actually a phone. A failed script, a disabled script or a desktop browser
   gets exactly today's behaviour.
4. **Surgical edits only** (CLAUDE.md invariant 6). No page is rewritten.
5. **Physics the owner already knows.** Not novelty — the iOS sheet: a drag
   follows the finger, a release is projected by its own velocity and snaps to
   the nearest stop, and pulling past the end meets resistance.

## 3. Architecture

### 3.1 The switch

`site/mobile.js` tests `(max-width: 920px) and (pointer: coarse)` and, only on
a match, sets `wl-app` on `<html>`. **Every new CSS rule hangs off that
class.** The class is the contract: no class, no phone layer, no risk to
desktop.

Playwright's `mobile` project is `devices["Pixel 7"]` — touch, 412×915 — so it
matches the query, and the existing 150 tests become the regression net rather
than an obstacle.

### 3.2 The sheet

The panel is fixed to the bottom at the height of its **largest** stop and
translated down to expose only the current one. The browser therefore
interpolates a single `transform` and never a layout — no animation library,
no `requestAnimationFrame` loop.

Stops, ascending, in pixels:

| Tool | Stop 0 (dock) | Stop 1 | Stop 2 |
|---|---|---|---|
| Price Split / Team Rate | grabber + summary strip | `min(52dvh, full)` | `min(88dvh, content)` |
| Console | 118px | `min(82dvh, content)` | — |

Behaviour:

- **Drag** on the head, or on the body while its scroller is at the top and
  the finger is moving down — otherwise the content scrolls. This is the
  standard coordination and the reason the body listener checks `scrollTop`.
- **Axis lock** after 10px, so a sheet drag never steals a scroll.
- **Release:** velocity is taken over the tail of the gesture (px/ms) and the
  position projected 120ms forward, then snapped to the nearest stop. A fling
  therefore crosses stops; a slow drag does not.
- **Rubber band** past either end at 0.36 resistance.
- **Scrim** fades in proportionally past the dock; tapping it collapses.
- **Tap still toggles.** The gesture is an addition, never a replacement for a
  control that already exists and is already tested.
- `prefers-reduced-motion: reduce` → duration 0 everywhere, snapping intact.
- `navigator.vibrate(8)` on snap. Android honours it. **iOS Safari has no
  Vibration API**; the haptic is a bonus, never the feedback itself.

### 3.3 The dock summary

The always-visible strip mirrors figures the page already renders, via
`MutationObserver` on those nodes. It therefore needs no hook into three
different render functions and inherits every translation for free.

Which figures appear is one attribute per page — the only HTML edit the sheet
needs:

```html
<div class="sticky" data-dock="figPay,figShare">   <!-- price.html -->
<div class="sticky" data-dock="figRate,figPeople"> <!-- team.html  -->
```

### 3.4 Swipe to delete a role

Rows are rebuilt by each page on every render, and page CSS addresses them by
position (`.role > :nth-child(6)`). **Nothing may restructure a row** — a
wrapper would break that selector silently.

So: one shared action pane is parked under whichever row is being swiped
(`#rows` gets `position: relative`), the row translates to reveal it, and
confirming clicks the remove button **that row already has**. All state logic
stays in the page, where it already lives and is already tested.

- Axis lock at 10px; a vertical drag is released to the scroller untouched.
- Opens one way only; the other direction gets rubber band.
- Latches open past 45% of the 92px pane; **a second tap confirms.**
- Mirrored in RTL.

**Decision: reveal-then-tap, not full-swipe-to-delete.** One careless thumb
should not cost a role. The confirm tap removes the whole class of accident
for the price of one tap.

### 3.5 Fundamentals — all nine pages

- `viewport-fit=cover`; safe-area insets on the dock, sheet and footer.
- `inputmode="decimal"` on the six number fields; `enterkeyhint`.
- **16px minimum input font-size under `(pointer: coarse)`** — this, and only
  this, is what stops iOS zooming on focus.
- 44px minimum touch targets: row delete, mode buttons, split-bar grips.
- `dvh` with a `vh` fallback.
- `overscroll-behavior: contain` **on the sheet only** — site-wide
  pull-to-refresh survives.
- `-webkit-tap-highlight-color: transparent` **paired with** explicit
  `:active` states. Feedback is replaced, never removed.

### 3.6 Installable

`manifest.webmanifest`: `display: standalone`, `start_url: "/"`, 192/512/
maskable icons generated from the existing asterisk mark, `theme_color` metas
for both schemes, and the `apple-mobile-web-app-*` metas iOS needs.

**No service worker** (decided). Nothing to invalidate, no stale-asset class
of bug, no cache versioning tied to the release number.

## 4. Files

**New:** `site/mobile.js` · `site/manifest.webmanifest` · three icons ·
`tests/e2e/mobile-app.spec.mjs`

**Edited:** `site/welance.css` (one `wl-app` section) · nine `<head>`s
(viewport, theme-color, manifest, apple metas) · `price.html`, `team.html`
(`data-dock`, script tag, `inputmode`) · `console.html` (script tag) ·
`calculators.html` (script tag).

## 5. Testing

New `tests/e2e/mobile-app.spec.mjs`, mobile project: dock visible without
scrolling; drag to half reveals the split bar; scrim collapses; swipe reveals
delete and confirming removes the row; the 16px input floor holds; the
manifest resolves without reaching an external host; reduced-motion snaps
instantly.

All 150 existing tests stay green. Expected friction, to be fixed rather than
worked around:

- mobile assertions that assume the result card sits in the document flow;
- anything the fixed dock now covers — answered by `body` bottom padding equal
  to the dock height plus the safe-area inset;
- the existing "no page reaches an unexpected external host" test, which the
  manifest and its icons must not violate.

## 6. Rejected

- **Horizontal swipe between the three calculators.** Needs a router or
  preloaded siblings, and horizontal swipe on a form page is a scroll-conflict
  trap. A compact tool switcher in the dock does the same job.
- **Full-swipe-to-delete without confirmation.** See 3.4.
- **Duplicate mobile markup.** See principle 2.
- **A service worker.** See 3.6.
