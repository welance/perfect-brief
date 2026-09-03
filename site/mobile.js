/* The phone layer.
 *
 * On a phone the console had one defect: the verdict left the screen. It
 * keeps its compact draggable verdict because that interaction fits a single
 * scrolling document. The layer only turns on when JS runs AND the device is
 * actually a phone, so a failed script or a desktop browser gets exactly the
 * old behaviour — every rule in welance.css hangs off the .wl-app class set
 * below.
 *
 * The console physics are the ones a phone owner already knows: a drag follows the
 * finger, a release is projected forward by its own velocity and snaps to the
 * nearest stop, and pulling past the end meets resistance instead of a wall.
 * That is what iOS does, and the curve below is its curve. No animation
 * library, no rAF loop — the browser interpolates one transform.
 */
(function (root, doc) {
  "use strict";

  var MQ = "(max-width: 920px)";
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

  /* --- the sheet ----------------------------------------------------------
   * `el` is the panel the page already has. It is fixed to the bottom at the
   * height of its largest stop and translated down to expose only the current
   * one, so the browser animates a single transform and never a layout.
   * `stops()` returns exposed heights in px, ascending; index 0 is the dock.
   */
  function Sheet(el, opts) {
    var head = opts.head;              /* the drag surface */
    var body = opts.body;              /* the scroller inside, may be null */
    var at = 0;                        /* index of the current stop */
    var stops = [];
    var dragging = false, moved = false, axis = null;
    var startY = 0, startPos = 0, pos = 0, hist = [];
    var scrim = doc.createElement("div");

    scrim.className = "wl-scrim";
    scrim.addEventListener("click", function () { go(0); });
    doc.body.appendChild(scrim);

    function measure() {
      stops = opts.stops();
      var tall = stops[stops.length - 1];
      el.style.height = tall + "px";
      /* the page must not end underneath the dock */
      doc.body.style.paddingBottom = "calc(" + (stops[0] + 24) + "px + env(safe-area-inset-bottom))";
      place(stops[Math.min(at, stops.length - 1)], false);
    }

    /* translate so that `expose` px of the sheet stand above the bottom edge */
    function place(expose, animate) {
      pos = expose;
      var tall = stops[stops.length - 1];
      el.style.transition = animate && !calm() ? "transform " + DUR + "ms " + EASE : "none";
      el.style.transform = "translate3d(0," + (tall - expose) + "px,0)";
      var open = expose > stops[0] + 4;
      scrim.style.opacity = open ? String(Math.min(1, (expose - stops[0]) / (tall - stops[0]))) : "0";
      scrim.style.pointerEvents = open ? "auto" : "none";
      el.classList.toggle("is-open", open);
      /* the console's own collapsed styling stays the source of truth there */
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

    /* a drag on the body only owns the gesture while its scroller is at the
       top and the finger is going down — otherwise the content scrolls */
    function bodyMayDrag(dy) {
      if (!body) return true;
      if (at === 0) return true;
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
        /* a drag that starts in the scrollable body may belong to it */
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
      if (!moved) return;                        /* a tap, not a drag */
      /* velocity over the tail of the gesture, px per ms, up is positive */
      var a = hist[0], b = hist[hist.length - 1];
      var span = b.t - a.t;
      var v = span > 0 ? (a.y - b.y) / span : 0;
      go(nearest(pos + v * FLING));
    }

    function wire(node) {
      if (!node) return;
      node.addEventListener("pointerdown", down);
      node.addEventListener("pointermove", move);
      node.addEventListener("pointerup", up);
      node.addEventListener("pointercancel", up);
    }
    wire(head);
    wire(body);

    /* tapping the handle still toggles — the gesture is an addition, never a
       replacement for the control that was already there and already tested */
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

  /* --- wiring the console -------------------------------------------------- */

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
        var wasCollapsed = panel.classList.contains("collapsed");
        panel.classList.remove("collapsed");
        var full = Math.min(vh(0.82), panel.scrollHeight);
        panel.classList.toggle("collapsed", wasCollapsed);
        return [118, full];
      }
    });
  }

  function start() {
    doc.documentElement.classList.add("wl-app");
    var vstick = doc.getElementById("vstick");
    if (vstick) { root.WelanceSheet.console = console_(vstick); }
  }

  root.WelanceSheet = { Sheet: Sheet, vh: vh, calm: calm, rtl: rtl, rubber: rubber,
                        LOCK: LOCK, EASE: EASE, DUR: DUR, tap: tap };

  if (root.matchMedia && root.matchMedia(MQ).matches) {
    if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", start);
    else start();
  }
})(window, document);
