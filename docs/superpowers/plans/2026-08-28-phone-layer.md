# Phone Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the four tool pages behave like a native phone app — the result always in reach on a bottom sheet you drag — and bring all nine pages up to mobile fundamentals.

**Architecture:** No page is rewritten. `site/mobile.js` sets `wl-app` on `<html>` only when JS runs and the device is a phone; every new CSS rule hangs off that class. The result panel each page already has becomes a bottom sheet **in place** — same nodes, same listeners, same i18n. The sheet is fixed at the height of its largest stop and translated down to expose the current one, so the browser interpolates one `transform` and never a layout.

**Tech Stack:** Vanilla ES5-style JS in an IIFE (match `site/splitbar.js`), plain CSS custom properties, Pointer Events, `MutationObserver`, Playwright for tests. **No build step, no framework, no dependency.**

**Spec:** `docs/superpowers/specs/2026-08-28-mobile-app-layer-design.md`

## Global Constraints

- **welance is ALWAYS lowercase** — every file, comment, commit message, page.
- **`site/` is the one public surface.** Published by Pages *and* mounted by the FastAPI app at `/`. There is no separate console.
- **Surgical edits only.** Do not rewrite `site/*.html` from scratch (CLAUDE.md invariant 6).
- **No external hosts.** `tests/e2e/site.spec.mjs:107` fails the build if any page reaches a host outside the allowlist. The manifest and its icons must be same-origin.
- **No engine changes.** `brief_bar/`, `app/`, fixtures and the ruleset are out of scope. `make test` must stay at 107 passed / 10 skipped.
- **Vanilla only.** No npm dependency may be added to the site. `var`, function expressions, IIFE — match `site/splitbar.js`.
- **Tone for any user-visible string:** modest, no hype words. `site/index.html` is the reference.
- **All 150 existing e2e tests stay green.** They are the regression net, not an obstacle.
- **A draft of `site/mobile.js` already exists** in the working tree, unreferenced by any page. Task 3 replaces it wholesale with the reviewed version below; do not assume it is correct.

---

### Task 1: Mobile fundamentals across all nine pages

The `wl-app` layer is worthless if focusing an input zooms the page. This task fixes that class of defect first, on every page, with no gesture code at all.

**Files:**
- Modify: `site/index.html`, `site/rules.html`, `site/console.html`, `site/data.html`, `site/security.html`, `site/integrate.html`, `site/calculators.html`, `site/price.html`, `site/team.html` — the `<meta name="viewport">` line in each
- Modify: `site/price.html:282,284,312,315,326` and `site/team.html:219` — the six number inputs
- Modify: `site/welance.css` — append the coarse-pointer baseline
- Test: `tests/e2e/mobile-app.spec.mjs` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `viewport-fit=cover` on every page, so `env(safe-area-inset-*)` resolves for Tasks 2–5. No JS symbols.

- [ ] **Step 1: Write the failing test**

Create `tests/e2e/mobile-app.spec.mjs`:

```js
/* The phone layer. Runs in the `mobile` project (Pixel 7, touch).
 * Desktop keeps its own suite; nothing here should pass there. */
import { test, expect } from "@playwright/test";

const PAGES = ["/", "/rules.html", "/console.html", "/data.html", "/security.html",
               "/integrate.html", "/calculators.html", "/price.html", "/team.html"];

test.describe("the fundamentals a phone needs", () => {
  for (const path of PAGES) {
    test(`${path} allows the safe area to be read`, async ({ page }) => {
      await page.goto(path);
      const content = await page.locator('meta[name="viewport"]').getAttribute("content");
      expect(content).toContain("viewport-fit=cover");
    });
  }

  test("no input is small enough to make iOS zoom on focus", async ({ page }) => {
    for (const path of ["/price.html", "/team.html", "/console.html"]) {
      await page.goto(path);
      const small = await page.locator("input, select, textarea").evaluateAll((els) =>
        els.filter((el) => el.offsetParent !== null)
           .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 16)
           .map((el) => el.id || el.className || el.tagName));
      expect(small, `${path} has sub-16px fields: ${small.join(", ")}`).toEqual([]);
    }
  });

  test("every number field asks for the numeric keyboard", async ({ page }) => {
    for (const path of ["/price.html", "/team.html"]) {
      await page.goto(path);
      const missing = await page.locator('input[type="number"]').evaluateAll((els) =>
        els.filter((el) => el.getAttribute("inputmode") !== "decimal").map((el) => el.id));
      expect(missing, `${path} number fields without inputmode`).toEqual([]);
    }
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile`

Expected: FAIL. The viewport tests fail with `expected "width=device-width, initial-scale=1.0" to contain "viewport-fit=cover"`; the font-size test lists fields; the inputmode test lists `rate, capr, coef, floorc, payout` and `rate`.

- [ ] **Step 3: Add `viewport-fit=cover` to all nine pages**

Every page currently carries the identical line, so one pass does it:

```bash
cd site
export LC_ALL=C
for f in index.html rules.html console.html data.html security.html \
         integrate.html calculators.html price.html team.html; do
  sed -i '' 's|<meta name="viewport" content="width=device-width, initial-scale=1.0">|<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">|' "$f"
done
grep -h 'name="viewport"' *.html | sort -u
```

Expected output: exactly one line, ending `viewport-fit=cover">`.

- [ ] **Step 4: Add `inputmode` to the six number fields**

```bash
cd site
export LC_ALL=C
sed -i '' 's|<input type="number" |<input type="number" inputmode="decimal" enterkeyhint="done" |g' price.html team.html
grep -c 'inputmode="decimal"' price.html team.html
```

Expected: `price.html:5` and `team.html:1`.

- [ ] **Step 5: Add the coarse-pointer baseline to `site/welance.css`**

Append at the end of the file:

```css
/* --- what a finger needs -------------------------------------------------
   Three defects, one cause: these pages were drawn for a cursor. A 13.5px
   field is under the 16px floor iOS uses to decide whether to zoom the whole
   page on focus — and it never zooms back, so every tap on a number left the
   layout wrong. A 26px hit area is half what a thumb reliably lands on. And
   removing the tap highlight without putting something in its place would
   leave a control that never admits it was pressed.
   Gated on a coarse pointer, so nothing here reaches a mouse. */
@media (pointer: coarse) {
  input, select, textarea, button {
    font-size: max(16px, 1em);
  }
  /* the fields the calculators pack into a row are the ones that were worst */
  .role input, .role select,
  .comp input[type="number"],
  .rolebar input, .rolebar select {
    font-size: 16px;
    min-height: 44px;
  }
  /* a thumb, not a cursor */
  .role button, .comp button, .mode, .addbtn, .lang,
  .wl-theme, .code-copy, .code-tabs button {
    min-height: 44px;
    min-width: 44px;
  }
  .grip { width: 44px; margin-inline-start: -22px; }

  /* the highlight goes, and an honest pressed state replaces it */
  a, button, summary, .chip, .mode, [role="button"] {
    -webkit-tap-highlight-color: transparent;
  }
  button:active, .chip:active, .mode:active,
  a.btn:active, [role="button"]:active { opacity: .62; }

  /* iOS inflates text in landscape unless told not to */
  html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
}
```

- [ ] **Step 6: Run the new test and watch it pass**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile`

Expected: PASS, 11 tests.

- [ ] **Step 7: Run the whole suite — nothing else may move**

Run: `make test-all`

Expected: `107 passed, 10 skipped` (python), `pass 16` (engine), and **161 passed** for e2e (150 existing + 11 new). If an existing test now fails, fix the cause; do not weaken the test.

- [ ] **Step 8: Commit**

```bash
git add site/*.html site/welance.css tests/e2e/mobile-app.spec.mjs
git commit -m "feat(site): the fundamentals a phone needs

viewport-fit=cover on all nine pages so the safe area can be read;
inputmode=decimal on the six number fields; a 16px floor on every
control under a coarse pointer, which is what stops iOS zooming the
page on focus and never zooming back; 44px hit areas; a pressed state
to replace the tap highlight we remove."
```

---

### Task 2: The `wl-app` switch and the sheet's dress

CSS only. The sheet cannot move yet — this task proves the class gates everything and that desktop is untouched.

**Files:**
- Modify: `site/welance.css` — append the `wl-app` section
- Test: `tests/e2e/mobile-app.spec.mjs`

**Interfaces:**
- Consumes: Task 1's safe-area availability.
- Produces: the class contract every later task depends on —
  `html.wl-app` (set by JS), `.wl-sheet`, `.wl-sheet-body`, `.wl-grab`,
  `.wl-dock`, `.wl-dock-cell`, `.wl-dock-k`, `.wl-dock-v`, `.wl-scrim`,
  `.is-open`, `.wl-swipe-act`, `.wl-swipe-del`, `.wl-swiped`, `.wl-going`,
  `.wl-swipeable`.

- [ ] **Step 1: Write the failing test**

Add to `tests/e2e/mobile-app.spec.mjs`:

```js
test.describe("the layer is opt-in", () => {
  test("the phone layer announces itself on a phone", async ({ page }) => {
    await page.goto("/price.html");
    await expect(page.locator("html")).toHaveClass(/wl-app/);
  });

  test("the result panel is pinned to the bottom, not lost down the page", async ({ page }) => {
    await page.goto("/price.html");
    const sheet = page.locator(".sticky");
    await expect(sheet).toHaveClass(/wl-sheet/);
    const box = await sheet.boundingBox();
    const vh = page.viewportSize().height;
    // its top edge is on screen: the answer is visible without scrolling
    expect(box.y).toBeLessThan(vh);
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "opt-in"`

Expected: FAIL — `wl-app` is never set (no JS yet) and `.sticky` has no `wl-sheet` class.

- [ ] **Step 3: Append the `wl-app` section to `site/welance.css`**

```css
/* --- the phone layer -----------------------------------------------------
   Everything below is inert until site/mobile.js decides this is a phone and
   sets .wl-app on <html>. That class is the whole contract: no class, no
   layer, and a failed script leaves exactly the behaviour that shipped
   before. The sheet is fixed at the height of its largest stop and translated
   down to expose the current one, so the browser interpolates one transform
   and never a layout.
   ------------------------------------------------------------------- */
.wl-app .wl-sheet {
  position: fixed;
  inset-inline: 0;
  bottom: 0;
  z-index: 40;
  display: flex;
  flex-direction: column;
  margin: 0;
  background: var(--paper);
  border-top: 2px solid var(--ink);
  box-shadow: 0 -8px 28px rgba(0, 0, 0, .16);
  will-change: transform;
  padding-bottom: env(safe-area-inset-bottom);
}
/* the console's panel already carries its own chrome; it only needs placing */
.wl-app .wl-sheet-flat { box-shadow: 0 -8px 24px rgba(0, 0, 0, .14); }

/* the grab surface: a handle you can see, and the answer beside it */
.wl-app .wl-grab {
  flex: none;
  cursor: grab;
  touch-action: none;
  padding: 7px 0 0;
  background: var(--paper);
}
.wl-app .wl-grab::before {
  content: "";
  display: block;
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: var(--rule);
  margin: 0 auto 6px;
}
.wl-app .wl-sheet.is-open .wl-grab { cursor: grabbing; }

.wl-app .wl-dock {
  display: flex;
  align-items: baseline;
  gap: var(--sp-5);
  padding: 0 var(--sp-4) var(--sp-3);
}
.wl-app .wl-dock-cell { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.wl-app .wl-dock-k {
  font-family: var(--mono); font-size: 10px; letter-spacing: .09em;
  text-transform: uppercase; color: var(--ink-soft);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.wl-app .wl-dock-v {
  font-family: var(--mono); font-variant-numeric: tabular-nums;
  font-size: 21px; font-weight: 600; letter-spacing: -.02em;
}

/* the scroller inside. overscroll-behavior is contained HERE and nowhere
   else, so the page keeps its pull-to-refresh. */
.wl-app .wl-sheet-body {
  flex: 1 1 auto;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  padding: 0 var(--sp-4) var(--sp-4);
  touch-action: pan-y;
}
.wl-app .wl-sheet .card { border: 0; background: transparent; padding: 0; }
.wl-app .wl-sheet .card + .card { margin-top: var(--sp-6); }

.wl-scrim {
  position: fixed; inset: 0; z-index: 39;
  background: rgba(10, 10, 10, .38);
  opacity: 0; pointer-events: none;
  transition: opacity 340ms cubic-bezier(.32,.72,0,1);
}

/* --- swipe a row away ---------------------------------------------------
   One shared pane, parked under whichever row is being swiped. The rows are
   rebuilt on every render and page CSS addresses them by position
   (.role > :nth-child(6)), so nothing may restructure a row. */
.wl-app .wl-swipeable { position: relative; }
.wl-app .wl-swipeable .role {
  position: relative; z-index: 1;
  background: var(--surface);
  touch-action: pan-y;
}
.wl-app .wl-swipe-act {
  position: absolute; inset-inline-end: 0; z-index: 0;
  display: none; align-items: center; justify-content: flex-end;
}
.wl-app .wl-swipe-act.is-live { display: flex; }
.wl-app .wl-swipe-del {
  height: 100%; min-width: 92px; border: 0;
  background: var(--fail); color: #fff;
  font-family: var(--mono); font-size: 12px; letter-spacing: .06em;
  text-transform: uppercase; cursor: pointer;
}
.wl-app .role.wl-going {
  transition: opacity 180ms ease, transform 180ms ease;
  opacity: 0; transform: scaleY(.6);
}

@media (prefers-reduced-motion: reduce) {
  .wl-app .wl-sheet, .wl-scrim, .wl-app .role { transition: none !important; }
}
```

- [ ] **Step 4: Run the test and watch it still fail — for the right reason now**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "opt-in"`

Expected: still FAIL. The CSS exists but nothing sets `wl-app` or `wl-sheet`; that is Task 3's job. **This is the expected state** — the test is written ahead of its implementation on purpose.

- [ ] **Step 5: Verify desktop is genuinely untouched**

Run: `make test-e2e`

Expected: the two new "opt-in" tests fail; **all 150 original tests pass, on both projects.** If any desktop test moved, a rule escaped the `.wl-app` prefix — find it and prefix it.

- [ ] **Step 6: Commit**

```bash
git add site/welance.css tests/e2e/mobile-app.spec.mjs
git commit -m "feat(site): dress the phone sheet, gated behind .wl-app

CSS only and inert: every rule hangs off a class that nothing sets yet,
so a failed script leaves exactly today's behaviour. overscroll-behavior
is contained on the sheet's own scroller and nowhere else, so the page
keeps its pull-to-refresh."
```

---

### Task 3: The sheet primitive — drag, velocity, snap

**Files:**
- Create: `site/mobile.js` (replaces the unreviewed draft in the working tree)
- Modify: `site/price.html:14` and `site/team.html` — add `<script src="mobile.js"></script>` after `splitbar.js`
- Modify: `site/price.html:95` and `site/team.html:80` — add the `data-dock` attribute
- Test: `tests/e2e/mobile-app.spec.mjs`

**Interfaces:**
- Consumes: every class name from Task 2.
- Produces: `site/mobile.js`, an IIFE with no exports. Internally:
  `Sheet(el, opts) → { measure(), go(index, quiet) }` where
  `opts = { head: Element, body: Element|null, stops: () => number[], collapsedClass?: string, onMove?: (open: boolean) => void }`.
  `stops()` returns exposed heights in px, ascending, index 0 being the dock.
  Task 4 calls `dock()`, Task 5 calls `Sheet` with two stops, Task 6 calls `swipes()`.

- [ ] **Step 1: Write the failing test**

Add to `tests/e2e/mobile-app.spec.mjs`:

```js
/* Drag helper: Playwright's mouse emits pointer events, which is what the
   sheet listens for. Steps matter — one jump gives no velocity to measure. */
async function dragY(page, from, to, steps = 12) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  for (let i = 1; i <= steps; i++) {
    await page.mouse.move(from.x, from.y + ((to.y - from.y) * i) / steps);
  }
  await page.mouse.up();
}

test.describe("the sheet", () => {
  test("opens when dragged up and shows the split", async ({ page }) => {
    await page.goto("/price.html");
    const sheet = page.locator(".sticky");
    const grab = page.locator(".wl-grab");
    const before = (await sheet.boundingBox()).y;
    const g = await grab.boundingBox();
    await dragY(page, { x: g.x + g.width / 2, y: g.y + 4 },
                      { x: g.x + g.width / 2, y: g.y - 320 });
    await page.waitForTimeout(450);
    const after = (await sheet.boundingBox()).y;
    expect(after).toBeLessThan(before - 100);
    await expect(page.locator(".splitbar")).toBeInViewport();
  });

  test("tapping the scrim puts it back", async ({ page }) => {
    await page.goto("/price.html");
    const grab = page.locator(".wl-grab");
    const g = await grab.boundingBox();
    const shut = (await page.locator(".sticky").boundingBox()).y;
    await dragY(page, { x: g.x + g.width / 2, y: g.y + 4 },
                      { x: g.x + g.width / 2, y: g.y - 320 });
    await page.waitForTimeout(450);
    await page.locator(".wl-scrim").click({ position: { x: 10, y: 10 } });
    await page.waitForTimeout(450);
    expect((await page.locator(".sticky").boundingBox()).y).toBeCloseTo(shut, -1);
  });

  test("the page does not end underneath the dock", async ({ page }) => {
    await page.goto("/price.html");
    const pad = await page.evaluate(() =>
      parseFloat(getComputedStyle(document.body).paddingBottom));
    const dock = await page.locator(".wl-grab").evaluate((el) => el.offsetHeight);
    expect(pad).toBeGreaterThan(dock);
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "sheet"`

Expected: FAIL — `.wl-grab` never resolves; the locator times out.

- [ ] **Step 3: Write `site/mobile.js`**

Overwrite the draft entirely with this file. Note the four things that are easy to get wrong and are load-bearing: the body listener must yield to its own scroller (`bodyMayDrag`), the axis lock must precede any `preventDefault`, the click handler must ignore a click that ended a drag, and `measure()` must re-run on resize and rotation.

```js
/* The phone layer.
 *
 * On a phone these pages had one shared defect: the answer left the screen.
 * The calculators put the result in a second column, and under 920px that
 * column falls to the bottom of a long stack of inputs — so you drag a weight
 * and scroll to find out what it did. The console already solved this its own
 * way (.vstick becomes a bottom bar under 900px, .vhandle toggles the detail);
 * this file generalises that answer instead of adding a second one, and gives
 * it the gesture the pattern always implied.
 *
 * Nothing here rewrites the pages. The result panel each page already has
 * becomes a bottom sheet in place: same nodes, same listeners, same i18n. The
 * layer only turns on when JS runs AND the device is actually a phone, so a
 * failed script or a desktop browser gets exactly the old behaviour — every
 * new rule in welance.css hangs off the .wl-app class set below.
 *
 * The physics are the ones a phone owner already knows: a drag follows the
 * finger, a release is projected forward by its own velocity and snaps to the
 * nearest stop, and pulling past the end meets resistance instead of a wall.
 * That is what iOS does, and the curve below is its curve. No animation
 * library, no rAF loop — the browser interpolates one transform.
 */
(function (root, doc) {
  "use strict";

  var MQ = "(max-width: 920px) and (pointer: coarse)";
  var EASE = "cubic-bezier(.32,.72,0,1)";   /* the sheet curve */
  var DUR = 340;                             /* ms, one snap */
  var FLING = 120;                           /* ms of velocity to project */
  var LOCK = 10;                             /* px before a drag picks an axis */

  function calm() {
    return root.matchMedia && root.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }
  function tap() {
    /* Android honours this; iOS Safari has no Vibration API and never will
       from a web page. Feeling it is a bonus, never the feedback itself. */
    if (navigator.vibrate) { try { navigator.vibrate(8); } catch (e) {} }
  }
  function rtl() {
    return doc.documentElement.getAttribute("dir") === "rtl";
  }
  /* past the end, give ground slowly rather than stopping dead */
  function rubber(over) { return over * 0.36; }
  function vh(pct) {
    var h = root.visualViewport ? root.visualViewport.height : root.innerHeight;
    return Math.round(h * pct);
  }

  /* --- the sheet ---------------------------------------------------------- */
  function Sheet(el, opts) {
    var head = opts.head, body = opts.body;
    var at = 0, stops = [];
    var dragging = false, moved = false, axis = null;
    var startY = 0, startPos = 0, pos = 0, hist = [];
    var scrim = doc.createElement("div");

    scrim.className = "wl-scrim";
    scrim.addEventListener("click", function () { go(0); });
    doc.body.appendChild(scrim);

    function measure() {
      stops = opts.stops();
      el.style.height = stops[stops.length - 1] + "px";
      doc.body.style.paddingBottom =
        "calc(" + (stops[0] + 24) + "px + env(safe-area-inset-bottom))";
      place(stops[Math.min(at, stops.length - 1)], false);
    }

    function place(expose, animate) {
      pos = expose;
      var tall = stops[stops.length - 1];
      el.style.transition = animate && !calm() ? "transform " + DUR + "ms " + EASE : "none";
      el.style.transform = "translate3d(0," + (tall - expose) + "px,0)";
      var open = expose > stops[0] + 4;
      scrim.style.opacity = open
        ? String(Math.min(1, (expose - stops[0]) / (tall - stops[0]))) : "0";
      scrim.style.pointerEvents = open ? "auto" : "none";
      el.classList.toggle("is-open", open);
      if (opts.collapsedClass) el.classList.toggle(opts.collapsedClass, !open);
      if (opts.onMove) opts.onMove(open);
    }

    function go(i, quiet) {
      at = Math.max(0, Math.min(stops.length - 1, i));
      place(stops[at], true);
      if (!quiet) tap();
      if (head) head.setAttribute("aria-expanded", String(at > 0));
    }

    function nearest(to) {
      var best = 0, gap = Infinity;
      stops.forEach(function (s, i) {
        var d = Math.abs(s - to);
        if (d < gap) { gap = d; best = i; }
      });
      return best;
    }

    /* a drag inside the scroller belongs to the scroller unless it is already
       at the top and the finger is heading down */
    function bodyMayDrag(dy) {
      if (!body || at === 0) return true;
      return body.scrollTop <= 0 && dy > 0;
    }

    function down(e) {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      dragging = true; moved = false; axis = null;
      startY = e.clientY; startPos = pos;
      hist = [{ t: e.timeStamp, y: e.clientY }];
      el.style.transition = "none";
    }

    function move(e) {
      if (!dragging) return;
      var dy = e.clientY - startY;
      if (!axis) {
        if (Math.abs(dy) < LOCK) return;
        if (e.currentTarget === body && !bodyMayDrag(dy)) { dragging = false; return; }
        axis = "y";
        try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) {}
      }
      moved = true;
      hist.push({ t: e.timeStamp, y: e.clientY });
      if (hist.length > 6) hist.shift();
      var want = startPos - dy;
      var lo = stops[0], hi = stops[stops.length - 1];
      if (want > hi) want = hi + rubber(want - hi);
      if (want < lo) want = lo - rubber(lo - want);
      place(want, false);
      e.preventDefault();
    }

    function up(e) {
      if (!dragging) return;
      dragging = false;
      try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) {}
      if (!moved) return;                         /* a tap, not a drag */
      var a = hist[0], b = hist[hist.length - 1];
      var span = b.t - a.t;
      var v = span > 0 ? (a.y - b.y) / span : 0;  /* px/ms, up is positive */
      go(nearest(pos + v * FLING));
    }

    function wire(node) {
      if (!node) return;
      node.addEventListener("pointerdown", down);
      node.addEventListener("pointermove", move);
      node.addEventListener("pointerup", up);
      node.addEventListener("pointercancel", up);
    }
    wire(head); wire(body);

    /* tapping the handle still toggles — the gesture is an addition, never a
       replacement for a control that already exists and is already tested */
    if (head) {
      head.addEventListener("click", function () {
        if (moved) { moved = false; return; }
        go(at > 0 ? 0 : (stops.length > 2 ? 1 : stops.length - 1));
      });
    }

    root.addEventListener("resize", measure);
    root.addEventListener("orientationchange", measure);
    measure();
    go(0, true);
    return { measure: measure, go: go };
  }

  root.WelanceSheet = { Sheet: Sheet, vh: vh, calm: calm, rtl: rtl, rubber: rubber,
                        LOCK: LOCK, EASE: EASE, DUR: DUR, tap: tap };

  function calculator(panel) {
    var head = doc.createElement("div");
    head.className = "wl-grab";
    head.setAttribute("role", "button");
    head.setAttribute("tabindex", "0");
    head.setAttribute("aria-expanded", "false");

    var body = doc.createElement("div");
    body.className = "wl-sheet-body";
    while (panel.firstChild) body.appendChild(panel.firstChild);
    panel.appendChild(head);
    panel.appendChild(body);
    panel.classList.add("wl-sheet");

    head.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); head.click(); }
    });

    return new Sheet(panel, {
      head: head,
      body: body,
      stops: function () {
        var peek = head.offsetHeight || 64;
        var full = Math.min(vh(0.88), body.scrollHeight + peek);
        return [peek, Math.min(vh(0.52), full), full];
      }
    });
  }

  function start() {
    doc.documentElement.classList.add("wl-app");
    var panel = doc.querySelector(".sticky[data-dock]");
    if (panel) { root.WelanceSheet.calculator = calculator(panel); }
  }

  if (root.matchMedia && root.matchMedia(MQ).matches) {
    if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", start);
    else start();
  }
})(window, document);
```

- [ ] **Step 4: Wire the two calculators**

In `site/price.html`, after the `splitbar.js` script tag (line 14):

```html
<script src="splitbar.js"></script>
<script src="mobile.js"></script>
```

and on line 95 add the attribute naming the two figures the dock shows:

```html
    <div class="sticky" data-dock="figPay,figShare">
```

Do the same in `site/team.html`: add the script tag after its `splitbar.js` line, and change its `<div class="sticky">` to:

```html
    <div class="sticky" data-dock="figRate,figPeople">
```

- [ ] **Step 5: Run the sheet tests and watch them pass**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile`

Expected: PASS, including the two "opt-in" tests from Task 2 that were deliberately left failing. The dock will be an empty grabber bar — the summary is Task 4.

- [ ] **Step 6: Run the whole suite**

Run: `make test-all`

Expected: everything green. **The likely casualties are mobile tests that assume the result card sits in the document flow** — `site.spec.mjs` assertions about `.splitbar` or `.figures` visibility, and `calculators.spec.mjs`. If one fails because the element is now inside a collapsed sheet, the correct fix is to open the sheet in that test (`await page.locator(".wl-grab").click()`), not to loosen the assertion.

- [ ] **Step 7: Commit**

```bash
git add site/mobile.js site/price.html site/team.html tests/e2e/mobile-app.spec.mjs
git commit -m "feat(site): the result becomes a sheet you can drag

The calculators put their answer in a second column, and under 920px
that column fell to the bottom of a long stack of inputs: you dragged a
weight and scrolled to find out what it did. The panel is now pinned to
the bottom, dragged with the velocity you release it at and snapped to
the nearest of three stops. Same nodes, same listeners, same i18n — the
layer only exists when JS runs on a coarse pointer."
```

---

### Task 4: The dock summary

**Files:**
- Modify: `site/mobile.js`
- Test: `tests/e2e/mobile-app.spec.mjs`

**Interfaces:**
- Consumes: `Sheet` and `calculator()` from Task 3; `data-dock` from Task 3 Step 4.
- Produces: `dock(panel, ids) → Element` — a `.wl-dock` strip whose cells mirror the figure nodes named by `ids`, kept live by `MutationObserver`.

- [ ] **Step 1: Write the failing test**

```js
test.describe("the dock", () => {
  test("shows the answer without opening anything", async ({ page }) => {
    await page.goto("/price.html");
    const cells = page.locator(".wl-dock-cell");
    await expect(cells).toHaveCount(2);
    await expect(page.locator(".wl-dock-v").first()).not.toHaveText("—");
    await expect(cells.first()).toBeInViewport();
  });

  test("follows the figures as you change the inputs", async ({ page }) => {
    await page.goto("/price.html");
    const v = page.locator(".wl-dock-v").first();
    const before = await v.textContent();
    await page.fill("#rate", "250");
    await page.locator("#rate").blur();
    await expect(v).not.toHaveText(before);
    // and it agrees with the figure it mirrors
    await expect(v).toHaveText(await page.locator("#figPay").textContent());
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "dock"`

Expected: FAIL — `.wl-dock-cell` has count 0.

- [ ] **Step 3: Add `dock()` to `site/mobile.js`**

Insert before `function calculator(panel)`:

```js
  /* --- the dock's summary -------------------------------------------------
   * The strip that stays visible mirrors figures the page already renders, so
   * it needs no hook into that page's own code and inherits its translations.
   * Watching the nodes rather than being called by them is what keeps this
   * file independent of three different render functions.
   */
  function dock(panel, ids) {
    var strip = doc.createElement("div");
    strip.className = "wl-dock";
    var cells = ids.map(function (id) {
      var src = doc.getElementById(id);
      var cell = doc.createElement("div");
      cell.className = "wl-dock-cell";
      var k = doc.createElement("span"); k.className = "wl-dock-k";
      var v = doc.createElement("span"); v.className = "wl-dock-v";
      cell.appendChild(k); cell.appendChild(v);
      strip.appendChild(cell);
      return { src: src, k: k, v: v };
    });
    function sync() {
      cells.forEach(function (c) {
        if (!c.src) return;
        var label = c.src.parentNode.querySelector(".k");
        c.k.textContent = label ? label.textContent : "";
        c.v.textContent = c.src.textContent;
      });
    }
    var mo = new MutationObserver(sync);
    cells.forEach(function (c) {
      if (c.src) mo.observe(c.src, { childList: true, characterData: true, subtree: true });
    });
    sync();
    return strip;
  }
```

- [ ] **Step 4: Hang it on the grabber**

In `calculator()`, immediately after `head.setAttribute("aria-expanded", "false");` add:

```js
    var ids = (panel.getAttribute("data-dock") || "").split(",").filter(Boolean);
    head.appendChild(dock(panel, ids));
```

**Order matters:** this must run *before* the `while (panel.firstChild)` loop moves the panel's children into the body, because `dock()` resolves `#figPay` and `#figShare` by id from the document — moving them first is harmless, but appending the strip after the move would put it inside the scroller instead of on the grabber.

- [ ] **Step 5: Run the dock tests and watch them pass**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "dock"`

Expected: PASS, 2 tests.

- [ ] **Step 6: Check it in a language that is not English**

Run: `cd tests/e2e && npx playwright test site.spec.mjs --project=mobile -g "language"`

Expected: PASS. The dock's labels come from the page's own `.k` nodes, so they must switch with the language for free. If they do not, the label lookup is reaching the wrong node.

- [ ] **Step 7: Commit**

```bash
git add site/mobile.js tests/e2e/mobile-app.spec.mjs
git commit -m "feat(site): the dock keeps the answer on screen

Two figures stay visible while you edit, mirrored from the nodes the
page already renders. Watching them rather than being called by them
keeps this file independent of three different render functions — and
means the labels follow the language with no extra keys."
```

---

### Task 5: The console adopts the same sheet

**Files:**
- Modify: `site/mobile.js`
- Modify: `site/console.html` — add the script tag; remove the now-duplicated toggle wiring at line 792
- Test: `tests/e2e/mobile-app.spec.mjs`

**Interfaces:**
- Consumes: `Sheet` from Task 3.
- Produces: `console_(panel) → Sheet` with two stops, passing `collapsedClass: "collapsed"` so the console's existing `.collapsed` rules stay the source of truth for what is hidden.

- [ ] **Step 1: Write the failing test**

```js
test.describe("the console's verdict", () => {
  test("still toggles by tap, and now also by drag", async ({ page }) => {
    await page.goto("/console.html");
    const v = page.locator("#vstick");
    await expect(v).toHaveClass(/wl-sheet/);
    await expect(v).toHaveClass(/collapsed/);
    await page.locator("#vhandle").click();
    await page.waitForTimeout(450);
    await expect(v).not.toHaveClass(/collapsed/);
    await expect(page.locator(".track-wrap")).toBeInViewport();
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "console"`

Expected: FAIL — `#vstick` has no `wl-sheet` class.

- [ ] **Step 3: Add `console_()` to `site/mobile.js`**

Insert after `calculator()`:

```js
  function console_(panel) {
    /* the console already has its handle, its collapsed styling and its tests;
       it gains the drag and keeps everything else */
    var head = doc.getElementById("vhandle");
    panel.classList.add("wl-sheet", "wl-sheet-flat");
    return new Sheet(panel, {
      head: head,
      body: null,
      collapsedClass: "collapsed",
      stops: function () {
        return [118, Math.min(vh(0.82), panel.scrollHeight)];
      }
    });
  }
```

and extend `start()`:

```js
  function start() {
    doc.documentElement.classList.add("wl-app");
    var panel = doc.querySelector(".sticky[data-dock]");
    if (panel) { root.WelanceSheet.calculator = calculator(panel); }
    var vstick = doc.getElementById("vstick");
    if (vstick) { root.WelanceSheet.console = console_(vstick); }
  }
```

- [ ] **Step 4: Point the console at the module and drop its duplicate toggle**

Add the script tag to `site/console.html`, after `code.js`:

```html
<script src="mobile.js"></script>
```

Then at line 792, the page's own toggle now fights the sheet's. Replace:

```js
$("#vstick").classList.add("collapsed");syncVstickLabel();
$("#vhandle").addEventListener("click",()=>{$("#vstick").classList.toggle("collapsed");syncVstickLabel();});
```

with:

```js
/* the phone layer owns the open/closed state when it is present (mobile.js
   toggles .collapsed itself, and adds the drag); without it, this is still
   the only thing that opens the panel. */
$("#vstick").classList.add("collapsed");syncVstickLabel();
if(!document.documentElement.classList.contains("wl-app")){
  $("#vhandle").addEventListener("click",()=>{$("#vstick").classList.toggle("collapsed");syncVstickLabel();});
}
new MutationObserver(syncVstickLabel).observe($("#vstick"),{attributes:true,attributeFilter:["class"]});
```

The observer keeps the handle's label ("details" / "less") honest whichever code moved the sheet.

- [ ] **Step 5: Run the console tests and watch them pass**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "console"`

Expected: PASS.

- [ ] **Step 6: Run the console's own existing suite — it is the largest**

Run: `cd tests/e2e && npx playwright test console-score-button.spec.mjs site.spec.mjs --project=mobile`

Expected: PASS. `console-score-button.spec.mjs` takes ~21s; that is normal.

- [ ] **Step 7: Commit**

```bash
git add site/mobile.js site/console.html tests/e2e/mobile-app.spec.mjs
git commit -m "feat(site): the console's verdict joins the shared sheet

It had already found this answer for itself — a fixed bottom bar with a
handle. It keeps its collapsed styling and its label, and gains the drag,
so there is one sheet behaviour on the site instead of two."
```

---

### Task 6: Swipe a role away

**Files:**
- Modify: `site/mobile.js`
- Test: `tests/e2e/mobile-app.spec.mjs`

**Interfaces:**
- Consumes: `rubber`, `LOCK`, `EASE`, `DUR`, `calm`, `rtl`, `tap` from Task 3.
- Produces: `swipes(host)` — attaches to `#rows`; no return value.

- [ ] **Step 1: Write the failing test**

```js
async function dragX(page, from, dx, steps = 10) {
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  for (let i = 1; i <= steps; i++) await page.mouse.move(from.x + (dx * i) / steps, from.y);
  await page.mouse.up();
}

test.describe("swiping a role away", () => {
  test("reveals delete, and asks before it removes", async ({ page }) => {
    await page.goto("/team.html");
    const rows = page.locator("#rows .role");
    const n = await rows.count();
    const box = await rows.first().boundingBox();
    await dragX(page, { x: box.x + box.width - 30, y: box.y + box.height / 2 }, -110);
    await page.waitForTimeout(400);
    await expect(page.locator(".wl-swipe-act.is-live")).toBeVisible();
    await expect(rows).toHaveCount(n);           // nothing gone yet
    await page.locator(".wl-swipe-del").click();
    await page.waitForTimeout(400);
    await expect(rows).toHaveCount(n - 1);
  });

  test("a vertical drag scrolls and never opens the action", async ({ page }) => {
    await page.goto("/team.html");
    const box = await page.locator("#rows .role").first().boundingBox();
    await dragY(page, { x: box.x + box.width / 2, y: box.y + box.height / 2 },
                      { x: box.x + box.width / 2, y: box.y - 150 });
    await page.waitForTimeout(300);
    await expect(page.locator(".wl-swipe-act.is-live")).toHaveCount(0);
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "swiping"`

Expected: FAIL — `.wl-swipe-act` does not exist.

- [ ] **Step 3: Add `swipes()` to `site/mobile.js`**

Insert after `dock()`:

```js
  /* --- swipe a row away ---------------------------------------------------
   * The rows are rebuilt by each page on every render, so nothing here may
   * restructure them: page CSS addresses them by position (.role > :nth-child)
   * and a wrapper would break it silently. Instead one shared action pane is
   * parked under whichever row is being swiped, and confirming it clicks the
   * remove button that row already has — so the state logic stays in the page.
   */
  function swipes(host) {
    var pane = doc.createElement("div");
    pane.className = "wl-swipe-act";
    var btn = doc.createElement("button");
    btn.type = "button";
    btn.className = "wl-swipe-del";
    pane.appendChild(btn);
    host.appendChild(pane);
    host.classList.add("wl-swipeable");

    var row = null, open = null, x0 = 0, y0 = 0, dx = 0, axis = null;
    var WIDTH = 92;
    var GONE = "[aria-label='remove role'], [aria-label='remove']";

    function park(r) {
      pane.style.top = r.offsetTop + "px";
      pane.style.height = r.offsetHeight + "px";
      var src = r.querySelector(GONE);
      btn.textContent = (src && src.getAttribute("title")) || "Delete";
      pane.classList.add("is-live");
    }
    function slide(r, to, animate) {
      r.style.transition = animate && !calm() ? "transform " + DUR + "ms " + EASE : "none";
      r.style.transform = "translate3d(" + (rtl() ? -to : to) + "px,0,0)";
    }
    function shut(animate) {
      if (open) { slide(open, 0, animate); open.classList.remove("wl-swiped"); }
      open = null;
      pane.classList.remove("is-live");
    }

    btn.addEventListener("click", function () {
      if (!open) return;
      var del = open.querySelector(GONE);
      var victim = open;
      open = null;
      pane.classList.remove("is-live");
      victim.classList.add("wl-going");
      setTimeout(function () { if (del) del.click(); }, calm() ? 0 : 180);
    });

    host.addEventListener("pointerdown", function (e) {
      if (e.target.closest("input, select, button, a, .grip")) return;
      var r = e.target.closest(".role");
      if (!r) return;
      if (open && open !== r) shut(true);
      row = r; x0 = e.clientX; y0 = e.clientY; dx = 0; axis = null;
    });
    host.addEventListener("pointermove", function (e) {
      if (!row) return;
      var mx = e.clientX - x0, my = e.clientY - y0;
      if (!axis) {
        if (Math.abs(mx) < LOCK && Math.abs(my) < LOCK) return;
        axis = Math.abs(mx) > Math.abs(my) ? "x" : "y";
        if (axis === "y") { row = null; return; }   /* it was a scroll */
        park(row);
        try { host.setPointerCapture(e.pointerId); } catch (err) {}
      }
      dx = rtl() ? -mx : mx;
      if (dx > 0) dx = rubber(dx);                  /* it only opens one way */
      if (dx < -WIDTH) dx = -WIDTH - rubber(-WIDTH - dx);
      slide(row, dx, false);
      e.preventDefault();
    });
    function done(e) {
      if (!row || axis !== "x") { row = null; return; }
      try { host.releasePointerCapture(e.pointerId); } catch (err) {}
      if (dx < -WIDTH * 0.45) {
        open = row; row.classList.add("wl-swiped"); slide(row, -WIDTH, true); tap();
      } else {
        slide(row, 0, true); shut(false);
      }
      row = null;
    }
    host.addEventListener("pointerup", done);
    host.addEventListener("pointercancel", done);
    doc.addEventListener("pointerdown", function (e) {
      if (open && !e.target.closest(".wl-swipe-act") && !e.target.closest(".wl-swiped")) shut(true);
    }, true);
  }
```

and extend `start()` with:

```js
    var rows = doc.getElementById("rows");
    if (rows) swipes(rows);
```

- [ ] **Step 4: Run the swipe tests and watch them pass**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "swiping"`

Expected: PASS, 2 tests.

- [ ] **Step 5: Confirm the split bar still drags — the two gestures share a surface**

Run: `cd tests/e2e && npx playwright test calculators.spec.mjs team-rate-focus.spec.mjs --project=mobile`

Expected: PASS. `splitbar.js` grips are excluded by the `.grip` guard in the `pointerdown` filter; if a grip drag now moves a row instead, that guard is not matching.

- [ ] **Step 6: Commit**

```bash
git add site/mobile.js tests/e2e/mobile-app.spec.mjs
git commit -m "feat(site): swipe a role away, then confirm

One shared pane parked under the swiped row, because the rows are
rebuilt on every render and page CSS addresses them by position — a
wrapper would break that silently. Confirming clicks the remove button
the row already has, so all the state logic stays in the page. It asks
before it deletes: one careless thumb should not cost a role."
```

---

### Task 7: Installable

**Files:**
- Create: `site/manifest.webmanifest`, `site/icon-192.png`, `site/icon-512.png`, `site/icon-maskable-512.png`
- Modify: the nine `<head>`s — manifest link, theme-color metas, apple metas
- Test: `tests/e2e/mobile-app.spec.mjs`

**Interfaces:**
- Consumes: nothing.
- Produces: a same-origin manifest. No JS symbols.

- [ ] **Step 1: Write the failing test**

```js
test.describe("installable", () => {
  test("the manifest is served, parses, and its icons resolve", async ({ page, request }) => {
    await page.goto("/price.html");
    const href = await page.locator('link[rel="manifest"]').getAttribute("href");
    expect(href).toBe("/manifest.webmanifest");
    const res = await request.get(href);
    expect(res.status()).toBe(200);
    const m = await res.json();
    expect(m.display).toBe("standalone");
    expect(m.icons.length).toBeGreaterThanOrEqual(3);
    for (const icon of m.icons) {
      const r = await request.get(icon.src);
      expect(r.status(), `${icon.src} must be same-origin and present`).toBe(200);
    }
  });

  test("both themes declare a colour for the browser chrome", async ({ page }) => {
    await page.goto("/price.html");
    await expect(page.locator('meta[name="theme-color"]')).toHaveCount(2);
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "installable"`

Expected: FAIL — the manifest link does not exist.

- [ ] **Step 3: Generate the icons from the asterisk the site already uses**

The mark is in `site/chrome.js:72` as a 30×30 path. Render it at both sizes with the headless Chrome already on this machine — no new dependency:

```bash
cd /tmp
cat > icon.html <<'HTML'
<style>
 html,body{margin:0}
 body{width:512px;height:512px;display:flex;align-items:center;justify-content:center;background:#0a0a0a}
 svg{width:300px;height:300px;color:#ff7b51}
</style>
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 30 30"><path fill="currentColor" fill-rule="evenodd" d="m18.403 16.5 7.951 8.046-2.096 2.121-7.952-8.046V30h-2.965V18.621L5.39 26.667l-2.096-2.121 7.951-8.046H0v-3h11.245L3.294 5.454 5.39 3.333l7.952 8.046V0h2.964v11.379l7.952-8.046 2.096 2.121-7.951 8.046h11.245v3z" clip-rule="evenodd"/></svg>
HTML
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SITE=/Users/ricricucit/Documents/workspaces/welance/r001-15-welance-score/perfect-brief-service/site
"$CHROME" --headless --disable-gpu --screenshot="$SITE/icon-512.png" --window-size=512,512 --default-background-color=0 file:///tmp/icon.html
"$CHROME" --headless --disable-gpu --screenshot="$SITE/icon-192.png" --window-size=192,192 --default-background-color=0 file:///tmp/icon.html
# maskable needs the mark inside the safe circle — 60% instead of 300/512
sed -i '' 's/width:300px;height:300px/width:230px;height:230px/' /tmp/icon.html
"$CHROME" --headless --disable-gpu --screenshot="$SITE/icon-maskable-512.png" --window-size=512,512 --default-background-color=0 file:///tmp/icon.html
ls -l "$SITE"/icon-*.png
```

Expected: three PNGs, non-zero size. Open one and confirm it is a coral asterisk on near-black.

- [ ] **Step 4: Write `site/manifest.webmanifest`**

```json
{
  "name": "the brief bar",
  "short_name": "brief bar",
  "description": "An open ruleset for scoring digital product briefs, and the calculators that go with it.",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "background_color": "#0a0a0a",
  "theme_color": "#0a0a0a",
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

**welance stays lowercase**, here as everywhere.

- [ ] **Step 5: Link it from all nine pages**

Each page already carries `<link rel="stylesheet" href="welance.css">`. Insert the block before it:

```bash
cd site
export LC_ALL=C
for f in index.html rules.html console.html data.html security.html \
         integrate.html calculators.html price.html team.html; do
  python3 - "$f" <<'PY'
import sys
f = sys.argv[1]
s = open(f, encoding='utf-8').read()
anchor = '<link rel="stylesheet" href="welance.css">'
block = ('<link rel="manifest" href="/manifest.webmanifest">\n'
         '<link rel="apple-touch-icon" href="/icon-192.png">\n'
         '<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">\n'
         '<meta name="theme-color" content="#0d0d0d" media="(prefers-color-scheme: dark)">\n'
         '<meta name="apple-mobile-web-app-capable" content="yes">\n'
         '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
         '<meta name="apple-mobile-web-app-title" content="brief bar">\n')
if 'rel="manifest"' not in s:
    s = s.replace(anchor, block + anchor, 1)
    open(f, 'w', encoding='utf-8').write(s)
    print("linked", f)
PY
done
```

- [ ] **Step 6: Run the installable tests and watch them pass**

Run: `cd tests/e2e && npx playwright test mobile-app.spec.mjs --project=mobile -g "installable"`

Expected: PASS, 2 tests.

- [ ] **Step 7: Confirm nothing reaches off-origin**

Run: `cd tests/e2e && npx playwright test site.spec.mjs --project=mobile -g "external host"`

Expected: PASS. Every icon and the manifest are same-origin by construction; this test is the guard that keeps it that way.

- [ ] **Step 8: Commit**

```bash
git add site/manifest.webmanifest site/icon-*.png site/*.html tests/e2e/mobile-app.spec.mjs
git commit -m "feat(site): make it installable

A manifest, three icons drawn from the asterisk the site already uses,
and the metas iOS wants. Standalone display, so Add to Home Screen gives
a real window rather than a browser tab. No service worker: nothing to
invalidate, and no stale-asset bug to reason about later."
```

---

### Task 8: The whole thing, on a real page, in both themes

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/specs/2026-08-28-mobile-app-layer-design.md` — mark implemented
- Test: everything

**Interfaces:**
- Consumes: Tasks 1–7.
- Produces: nothing.

- [ ] **Step 1: Run the full offline suite**

Run: `make test-all`

Expected: `107 passed, 10 skipped`; `pass 16`; e2e **all green on both projects**.

- [ ] **Step 2: Run lint and typecheck**

Run: `.venv/bin/ruff check app brief_bar tests && .venv/bin/mypy app brief_bar`

Expected: `All checks passed!` and `Success: no issues found in 14 source files`. (The `make lint` / `make typecheck` targets do not use `.venv`, so they fail on PATH — a pre-existing quirk, not this work.)

- [ ] **Step 3: Look at it**

```bash
cd site && python3 -m http.server 8899 &
```

In a mobile-emulating browser at 412×915, on `price.html` and `team.html`:

- the two figures are readable without scrolling;
- a slow drag on the grabber follows the finger and settles at the middle stop;
- a fast flick from the dock crosses straight to full;
- pulling past full meets resistance rather than a wall;
- at full, scrolling the content works and only takes over the sheet at the top;
- the scrim darkens as it opens and closes it on tap;
- a role row swipes to reveal Delete and does nothing until the tap;
- **switch to dark and repeat** — the sheet, scrim and delete pane must all hold their ground.

Then `console.html`: the verdict bar taps open as before, and now also drags.

- [ ] **Step 4: Check reduced motion honestly**

In DevTools, emulate `prefers-reduced-motion: reduce`, then drag the sheet.

Expected: it still snaps to the right stop, with no animation. If it fails to move at all, `calm()` is being consulted somewhere it should not be.

- [ ] **Step 5: Update `CHANGELOG.md`**

Add under a new version heading, in the house voice — plain, no hype:

```markdown
## 1.12.0 — the answer stays on screen

- The calculators and the console get a phone layer: the result panel becomes
  a bottom sheet you drag, with the stop it lands on chosen by the velocity
  you let go at. Two figures stay visible in a dock while you edit.
- Roles can be swiped away, with a confirm tap so a careless thumb costs
  nothing.
- Mobile fundamentals on all nine pages: safe-area insets, a 16px input floor
  (which is what stopped iOS zooming the page on every focus), the numeric
  keyboard on number fields, 44px hit areas.
- Installable: a manifest, icons, standalone display. No service worker.
- Nothing changes on a desktop, and nothing changes if the script fails: the
  whole layer hangs off one class that only a phone with working JS ever gets.
```

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md docs/superpowers/specs/2026-08-28-mobile-app-layer-design.md
git commit -m "docs: the phone layer, in the changelog"
```

---

## Self-Review

**Spec coverage.** §1 findings → Task 1 (inputmode, 16px, viewport-fit) and Task 3 (the sticky defect). §3.1 the switch → Task 3 Step 3. §3.2 the sheet → Tasks 3 and 5. §3.3 the dock → Task 4. §3.4 swipe → Task 6. §3.5 fundamentals → Tasks 1 and 2. §3.6 installable → Task 7. §4 files → all tasks. §5 testing → every task's test step, with the expected-friction note landing in Task 3 Step 6. §6 rejected → nothing to implement. **No gaps.**

**Type consistency.** `Sheet(el, opts)` is defined once in Task 3 and called in Tasks 3 and 5 with the same option names (`head`, `body`, `stops`, `collapsedClass`, `onMove`). `dock(panel, ids)` is defined in Task 4 and called only there. `swipes(host)` is defined and called in Task 6. `calm`, `rtl`, `rubber`, `tap`, `vh`, `LOCK`, `EASE`, `DUR` are defined in Task 3 before any task uses them. The class names in Task 2's CSS are exactly those the JS sets.

**Known ordering trap, called out where it bites:** Task 4 Step 4 must insert the dock before `calculator()` moves the panel's children into the body.
