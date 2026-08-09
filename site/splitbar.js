/* A split you can grab.
 *
 * One bar, one segment per row, a handle on every boundary. Dragging a handle
 * moves weight from one row to its neighbour, so the total is not a rule the
 * reader has to keep — it is a property no gesture can break. Typing is gone
 * on purpose: a number field that means "1" next to another "1" tells you
 * nothing, and re-rendering the list on every keystroke ate the caret.
 *
 * Used by Perfect Price (the parts of a role) and Perfect Team (the roles in a
 * project). They are the same question — how does this whole divide? — so they
 * are the same control, in one file, instead of two that drift apart.
 *
 * Deliberately colourless: this is something you set, not something the model
 * concluded, so it borrows the page's own ink rather than the brand's colours,
 * which are spent on results. It follows the theme into the dark for free.
 */
(function (root) {
  "use strict";

  // The steps avoid the middle of the ramp on purpose: a 50% grey is where
  // neither the page's ink nor its paper reads on top of it.
  function tone(ink) {
    return {
      bg: "color-mix(in srgb, var(--ink) " + ink + "%, var(--paper))",
      fg: ink >= 55 ? "var(--paper)" : "var(--ink)"
    };
  }
  var TONES = [tone(12), tone(66), tone(26), tone(82), tone(40), tone(92)];

  /* --- keeping the whole whole ------------------------------------------- */

  function whole(rows) {
    // integers that still add to exactly 100 (largest remainder wins)
    if (!rows.length) return;
    var floors = rows.map(function (r) { return Math.floor(Math.max(0, r.weight)); });
    var short = 100 - floors.reduce(function (a, b) { return a + b; }, 0);
    var byFraction = rows.map(function (r, i) {
      return { i: i, frac: Math.max(0, r.weight) - Math.floor(Math.max(0, r.weight)) };
    }).sort(function (a, b) { return b.frac - a.frac; });
    for (var k = 0; k < short; k++) floors[byFraction[k % rows.length].i]++;
    for (var j = 0; j > short; j--) {  // over 100: take back from the largest
      var big = floors.indexOf(Math.max.apply(null, floors));
      if (floors[big] > 0) floors[big]--;
    }
    rows.forEach(function (r, i) { r.weight = floors[i]; });
  }

  function rescale(rows) {
    // after adding or removing: keep the proportions, restore the whole
    if (!rows.length) return;
    var sum = rows.reduce(function (a, r) { return a + Math.max(0, r.weight); }, 0);
    rows.forEach(function (r) {
      r.weight = sum > 0 ? Math.max(0, r.weight) * 100 / sum : 100 / rows.length;
    });
    whole(rows);
  }

  function setShare(rows, i, value) {
    var v = Math.max(0, Math.min(100, Math.round(value) || 0));
    if (rows.length === 1) { rows[0].weight = 100; return; }
    var rest = 100 - v;
    var others = rows.filter(function (_, j) { return j !== i; });
    var sum = others.reduce(function (a, r) { return a + Math.max(0, r.weight); }, 0);
    others.forEach(function (r) {
      r.weight = sum > 0 ? rest * Math.max(0, r.weight) / sum : rest / others.length;
    });
    rows[i].weight = v;
    whole(rows);
  }

  /* --- the control -------------------------------------------------------- */

  /* mount(host, opts)
   *   opts.rows()      → the array being divided; each item has a `weight`
   *   opts.name(i)     → what to call row i in the label and the screen reader
   *   opts.onChange()  → called after every change, once the numbers are whole
   *   opts.tip         → title text for the bar as a whole
   *   opts.gripLabel(a, b) → accessible name for the handle between two rows
   * Returns { rebuild, paint }: rebuild when the number of rows changes,
   * paint when only the numbers did.
   */
  function mount(host, opts) {
    var rtl = function () {
      return getComputedStyle(document.documentElement).direction === "rtl";
    };

    function rows() { return opts.rows(); }
    function name(i) { return opts.name(i); }

    function moveBoundary(i, delta) {
      // give what one row loses to the next, and never below nothing
      var a = rows()[i], b = rows()[i + 1];
      var d = Math.max(-a.weight, Math.min(b.weight, Math.round(delta)));
      a.weight += d; b.weight -= d;
    }

    function makeGrip(i) {
      var g = document.createElement("button");
      g.type = "button"; g.className = "grip";
      g.setAttribute("role", "slider");
      g.setAttribute("aria-valuemin", "0");
      g.setAttribute("aria-valuemax", "100");

      function ratioAt(clientX) {
        var box = host.getBoundingClientRect();
        var r = (clientX - box.left) / box.width;
        if (rtl()) r = 1 - r;
        return Math.max(0, Math.min(1, r));
      }
      function before() {
        return rows().slice(0, i).reduce(function (a, r) { return a + r.weight; }, 0);
      }

      g.addEventListener("pointerdown", function (e) {
        g.setPointerCapture(e.pointerId);
        g.classList.add("dragging");
        host.classList.remove("smooth");  // follow the finger exactly
        e.preventDefault();
      });
      g.addEventListener("pointermove", function (e) {
        if (!g.hasPointerCapture(e.pointerId)) return;
        moveBoundary(i, ratioAt(e.clientX) * 100 - before() - rows()[i].weight);
        paint(); opts.onChange();
      });
      function end(e) {
        if (g.hasPointerCapture(e.pointerId)) g.releasePointerCapture(e.pointerId);
        g.classList.remove("dragging");
        host.classList.add("smooth");
        opts.onChange();
      }
      g.addEventListener("pointerup", end);
      g.addEventListener("pointercancel", end);

      // the same control, from the keyboard
      g.addEventListener("keydown", function (e) {
        var step = e.shiftKey ? 10 : 1;
        var by = { ArrowLeft: -step, ArrowRight: step, ArrowDown: -step, ArrowUp: step,
                   PageDown: -10, PageUp: 10 }[e.key];
        if (by === undefined) return;
        if (rtl() && (e.key === "ArrowLeft" || e.key === "ArrowRight")) by = -by;
        e.preventDefault();
        moveBoundary(i, by);
        paint(); opts.onChange();
      });
      return g;
    }

    function rebuild() {
      host.textContent = "";
      if (opts.tip) host.title = opts.tip;
      rows().forEach(function (r, i) {
        var seg = document.createElement("div");
        seg.className = "effortseg";
        var c = TONES[i % TONES.length];
        seg.style.background = c.bg;
        seg.style.color = c.fg;
        var label = document.createElement("span");
        label.className = "effortlabel";
        seg.appendChild(label);
        host.appendChild(seg);
      });
      for (var i = 0; i < rows().length - 1; i++) host.appendChild(makeGrip(i));
      paint();
    }

    function paint() {
      var segs = host.querySelectorAll(".effortseg");
      rows().forEach(function (r, i) {
        var seg = segs[i];
        if (!seg) return;
        seg.style.flexBasis = r.weight + "%";
        seg.dataset.share = String(r.weight);
        seg.title = name(i) + " · " + r.weight + "%";
      });
      // what fits is a question about pixels, not percentages: 25% of a phone
      // is not 25% of a laptop. Ask the segment how wide it actually is.
      rows().forEach(function (r, i) {
        var seg = segs[i];
        if (!seg) return;
        var room = seg.getBoundingClientRect().width;
        var full = name(i) + " · " + r.weight + "%";
        seg.querySelector(".effortlabel").textContent =
          room >= full.length * 6.6 ? full : (room >= 34 ? r.weight + "%" : "");
      });
      var at = 0;
      host.querySelectorAll(".grip").forEach(function (g, i) {
        at += rows()[i].weight;
        g.style.insetInlineStart = at + "%";
        g.setAttribute("aria-valuenow", String(at));
        g.setAttribute("aria-valuetext",
          name(i) + " " + rows()[i].weight + "%, " + name(i + 1) + " " + rows()[i + 1].weight + "%");
        g.setAttribute("aria-label", opts.gripLabel(name(i), name(i + 1)));
      });
    }

    rebuild();
    return { rebuild: rebuild, paint: paint };
  }

  root.WelanceSplitBar = {
    mount: mount, whole: whole, rescale: rescale, setShare: setShare, TONES: TONES
  };
})(window);
