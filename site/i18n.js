/* Welance site i18n — one language, everywhere.
 *
 * How it works, in one read:
 *   - English lives in the markup and is the content of record.
 *   - Each other language is one flat file in i18n/<code>.js that calls
 *     WelanceI18n.register(code, { reviewed, strings }). A native speaker
 *     can correct their language in a plain PR against that one file —
 *     that IS the review gate: `reviewed: false` shows a draft badge in
 *     the switcher until a native speaker has passed over the file.
 *   - Elements opt in with data-i18n="key" (text) or data-i18n-html="key"
 *     (string may contain inline <b>/<em>/<a> markup, from our own
 *     dictionaries only — never from user input).
 *   - The choice is stored in localStorage["welance-lang"], readable from
 *     ?lang=, and sets lang/dir on <html> (Urdu and Arabic are RTL).
 *   - price.html and console.html keep their own (older) i18n engines and
 *     sync on the same storage key, so the choice follows you across pages.
 *
 * No dependencies, no build step. Include i18n.js first, then the
 * dictionary files; everything applies on DOMContentLoaded.
 */
(function (root) {
  "use strict";

  var LANGS = [
    { code: "en",    name: "English",        dir: "ltr" },
    { code: "de",    name: "Deutsch",        dir: "ltr" },
    { code: "it",    name: "Italiano",       dir: "ltr" },
    { code: "ur",    name: "اردو",           dir: "rtl" },
    { code: "pt-BR", name: "Português (BR)", dir: "ltr" },
    { code: "vi",    name: "Tiếng Việt",     dir: "ltr" },
    { code: "ar",    name: "عربي",           dir: "rtl" },
    { code: "es",    name: "Español",        dir: "ltr" }
  ];
  var STORE = "welance-lang";
  var dicts = {};
  var current = "en";
  var warned = {};

  function meta(code) {
    return LANGS.filter(function (l) { return l.code === code; })[0] || null;
  }

  function register(code, dict) { dicts[code] = dict; }

  function t(key) {
    var d = dicts[current];
    if (d && d.strings && Object.prototype.hasOwnProperty.call(d.strings, key)) {
      return d.strings[key];
    }
    if (current !== "en" && !warned[current + ":" + key]) {
      warned[current + ":" + key] = true;
      if (root.console && console.warn) console.warn("i18n: no " + current + " string for " + key);
    }
    return null; // caller keeps its English
  }

  function applyNodes() {
    // English from the markup is cached per node on first pass, so
    // switching back to en always restores the content of record.
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      if (el._wlEn === undefined) el._wlEn = el.textContent;
      var v = current === "en" ? null : t(el.getAttribute("data-i18n"));
      el.textContent = v !== null ? v : el._wlEn;
    });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      if (el._wlEnH === undefined) el._wlEnH = el.innerHTML;
      var v = current === "en" ? null : t(el.getAttribute("data-i18n-html"));
      el.innerHTML = v !== null ? v : el._wlEnH;
    });
  }

  function renderSwitcher() {
    var host = document.getElementById("langswitch");
    if (!host) return;
    host.textContent = "";
    LANGS.forEach(function (l) {
      var b = document.createElement("button");
      b.type = "button";
      b.className = "wl-lang";
      b.textContent = l.name;
      b.setAttribute("aria-pressed", l.code === current ? "true" : "false");
      var d = dicts[l.code];
      if (l.code !== "en" && d && d.reviewed === false) {
        var s = document.createElement("sup");
        s.className = "wl-draft";
        s.textContent = "draft";
        s.title = "machine-drafted — awaiting native-speaker review";
        b.appendChild(s);
      }
      b.addEventListener("click", function () { set(l.code); });
      host.appendChild(b);
    });
  }

  function set(code) {
    if (!meta(code)) code = "en";
    current = code;
    try { localStorage.setItem(STORE, code); } catch (e) {}
    var m = meta(code);
    document.documentElement.setAttribute("lang", code);
    document.documentElement.setAttribute("dir", m.dir);
    applyNodes();
    renderSwitcher();
    document.dispatchEvent(new CustomEvent("welance:lang", { detail: { lang: code, dir: m.dir } }));
  }

  function initial() {
    try {
      var q = new URLSearchParams(location.search).get("lang");
      if (q && meta(q)) return q;
      var s = localStorage.getItem(STORE);
      if (s && meta(s)) return s;
    } catch (e) {}
    return "en";
  }

  root.WelanceI18n = {
    LANGS: LANGS, STORE: STORE,
    register: register, t: t, set: set,
    get lang() { return current; },
    get dir() { return (meta(current) || LANGS[0]).dir; }
  };

  function boot() { set(initial()); }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof self !== "undefined" ? self : globalThis);
