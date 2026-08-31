/* The phone layer.
 *
 * On a phone these pages had one shared defect: the answer left the screen.
 * The calculators now become a focused Edit/Answer workspace: one input
 * section at a time, one explicit result, and one fixed live summary carrying
 * only the amount, compressed split and percentage/margin. The console keeps
 * its compact draggable verdict because that interaction fits its single
 * scrolling document rather than a multi-section calculator.
 *
 * Nothing here duplicates calculator markup: the existing sections and result
 * nodes are rearranged in place, keeping their listeners and translations.
 * The layer only turns on when JS runs AND the device is actually a phone, so a
 * failed script or a desktop browser gets exactly the old behaviour — every
 * new rule in welance.css hangs off the .wl-app class set below.
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
      /* renderRows() clears this host whenever locale or state changes. */
      if (pane.parentNode !== host) host.appendChild(pane);
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
      if (e.target.closest("button, a, .grip")) return;
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
      if (dx > 0) dx = rubber(dx);                  /* only opens one way */
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

  /* --- wiring the three tools --------------------------------------------- */

  var WORDS = {
    en: ["Edit", "Answer", "Section", "of", "Previous", "Next", "Technical details"],
    de: ["Bearbeiten", "Ergebnis", "Abschnitt", "von", "Zurück", "Weiter", "Technische Details"],
    it: ["Modifica", "Risultato", "Sezione", "di", "Indietro", "Avanti", "Dettagli tecnici"],
    es: ["Editar", "Resultado", "Sección", "de", "Anterior", "Siguiente", "Detalles técnicos"],
    ar: ["تعديل", "النتيجة", "القسم", "من", "السابق", "التالي", "تفاصيل تقنية"],
    ur: ["ترمیم", "نتیجہ", "حصہ", "از", "پچھلا", "اگلا", "تکنیکی تفصیل"],
    vi: ["Sửa", "Kết quả", "Phần", "trên", "Trước", "Tiếp", "Chi tiết kỹ thuật"],
    zh: ["编辑", "结果", "部分", "/", "上一步", "下一步", "技术细节"],
    pt: ["Editar", "Resultado", "Seção", "de", "Anterior", "Seguinte", "Detalhes técnicos"]
  };

  function words() {
    var lang = (doc.documentElement.lang || "en").toLowerCase().split("-")[0];
    return WORDS[lang] || WORDS.en;
  }

  function compactDetails(panel, label) {
    var first = panel.querySelector(":scope > .card");
    if (!first) return;
    var details = doc.createElement("details");
    details.className = "wl-calc-details";
    var summary = doc.createElement("summary");
    summary.textContent = label;
    details.appendChild(summary);

    [first.querySelector(".ladder"), first.querySelector(".splitkey"),
     first.querySelector(".formula")].forEach(function (node) {
      if (node) details.appendChild(node);
    });
    while (first.nextElementSibling) details.appendChild(first.nextElementSibling);
    if (details.children.length > 1) panel.appendChild(details);
    return summary;
  }

  function liveFooter(panel, kind, showAnswer) {
    var amountId = kind === "team" ? "figRate" : "figPay";
    var secondId = kind === "team" ? "figMargin" : "figShare";
    var amountSrc = doc.getElementById(amountId);
    var secondSrc = doc.getElementById(secondId);
    var sourceBar = panel.querySelector(".splitbar");
    var button = doc.createElement("button");
    button.type = "button";
    button.className = "wl-answer-footer";

    var amount = doc.createElement("span"); amount.className = "wl-answer-main";
    var key = doc.createElement("span"); key.className = "wl-answer-k";
    var value = doc.createElement("strong"); value.className = "wl-answer-v";
    amount.appendChild(key); amount.appendChild(value);
    var bar = doc.createElement("span"); bar.className = "wl-answer-bar"; bar.setAttribute("aria-hidden", "true");
    var second = doc.createElement("strong"); second.className = "wl-answer-side";
    button.appendChild(amount); button.appendChild(bar); button.appendChild(second);
    doc.body.appendChild(button);

    function sync() {
      var label = amountSrc && amountSrc.parentNode.querySelector(".k");
      key.textContent = label ? label.textContent : "";
      value.textContent = amountSrc ? amountSrc.textContent : "—";
      second.textContent = secondSrc ? secondSrc.textContent : "—";
      bar.textContent = "";
      if (sourceBar) Array.prototype.forEach.call(sourceBar.children, function (part) {
        var bit = doc.createElement("i");
        var style = root.getComputedStyle(part);
        bit.style.backgroundColor = style.backgroundColor;
        bit.style.flexBasis = part.style.flexBasis || style.flexBasis || "0%";
        bit.style.flexGrow = "0"; bit.style.flexShrink = "0";
        bar.appendChild(bit);
      });
      button.setAttribute("aria-label", key.textContent + " " + value.textContent + ", " + second.textContent);
    }
    var mo = new MutationObserver(sync);
    if (amountSrc) mo.observe(amountSrc, { childList: true, characterData: true, subtree: true });
    if (secondSrc) mo.observe(secondSrc, { childList: true, characterData: true, subtree: true });
    if (sourceBar) mo.observe(sourceBar, { attributes: true, childList: true, subtree: true,
                                          attributeFilter: ["style", "class"] });
    button.addEventListener("click", showAnswer);
    sync();
    return button;
  }

  function calculator(panel) {
    var cols = panel.parentNode;
    var inputs = cols.firstElementChild;
    var sections = Array.prototype.filter.call(inputs.children, function (el) {
      return el.matches && el.matches("section.card");
    });
    var w = words(), at = 0, mode = "edit";
    var kind = panel.getAttribute("data-dock") === "figRate,figPeople" ? "team" : "price";
    var modes = doc.createElement("div"); modes.className = "wl-calc-modes";
    var edit = doc.createElement("button"); edit.type = "button"; edit.textContent = w[0];
    var answer = doc.createElement("button"); answer.type = "button"; answer.textContent = w[1];
    modes.appendChild(edit); modes.appendChild(answer);
    cols.parentNode.insertBefore(modes, cols);

    var steps = doc.createElement("div"); steps.className = "wl-calc-steps";
    var count = doc.createElement("span"); count.className = "wl-calc-count";
    var nav = doc.createElement("span"); nav.className = "wl-calc-nav";
    var prev = doc.createElement("button"); prev.type = "button"; prev.textContent = "←"; prev.setAttribute("aria-label", w[4]);
    var next = doc.createElement("button"); next.type = "button"; next.textContent = "→"; next.setAttribute("aria-label", w[5]);
    nav.appendChild(prev); nav.appendChild(next); steps.appendChild(count); steps.appendChild(nav);
    inputs.insertBefore(steps, inputs.firstChild);

    inputs.classList.add("wl-calc-inputs");
    panel.classList.add("wl-calc-answer");
    var detailSummary = compactDetails(panel, w[6]);

    function labels() {
      w = words();
      edit.textContent = w[0]; answer.textContent = w[1];
      prev.textContent = rtl() ? "→" : "←"; next.textContent = rtl() ? "←" : "→";
      prev.setAttribute("aria-label", w[4]); next.setAttribute("aria-label", w[5]);
      if (detailSummary) detailSummary.textContent = w[6];
    }

    function paint() {
      var editing = mode === "edit";
      inputs.hidden = !editing; panel.hidden = editing;
      edit.setAttribute("aria-pressed", String(editing));
      answer.setAttribute("aria-pressed", String(!editing));
      sections.forEach(function (section, i) { section.hidden = !editing || i !== at; });
      count.textContent = w[2] + " " + (at + 1) + " " + w[3] + " " + sections.length;
      prev.disabled = at === 0; next.disabled = at === sections.length - 1;
      doc.documentElement.classList.toggle("wl-answering", !editing);
    }
    function showEdit() { mode = "edit"; paint(); root.scrollTo({ top: modes.offsetTop, behavior: calm() ? "auto" : "smooth" }); }
    function showAnswer() { mode = "answer"; paint(); root.scrollTo({ top: modes.offsetTop, behavior: calm() ? "auto" : "smooth" }); }
    edit.addEventListener("click", showEdit); answer.addEventListener("click", showAnswer);
    prev.addEventListener("click", function () { if (at > 0) { at--; paint(); } });
    next.addEventListener("click", function () { if (at < sections.length - 1) { at++; paint(); } });
    liveFooter(panel, kind, showAnswer);
    doc.addEventListener("welance:lang", function () { labels(); paint(); });
    labels();
    paint();
    doc.body.style.paddingBottom = "calc(92px + env(safe-area-inset-bottom))";
    return { go: function (i) { if (i > 0) showAnswer(); else showEdit(); } };
  }

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
    var panel = doc.querySelector(".sticky[data-dock]");
    if (panel) { root.WelanceSheet.calculator = calculator(panel); }
    var vstick = doc.getElementById("vstick");
    if (vstick) { root.WelanceSheet.console = console_(vstick); }
    var rows = doc.getElementById("rows");
    if (rows) swipes(rows);
  }

  root.WelanceSheet = { Sheet: Sheet, vh: vh, calm: calm, rtl: rtl, rubber: rubber,
                        LOCK: LOCK, EASE: EASE, DUR: DUR, tap: tap };

  if (root.matchMedia && root.matchMedia(MQ).matches) {
    if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", start);
    else start();
  }
})(window, document);
