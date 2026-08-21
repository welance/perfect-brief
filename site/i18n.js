/* welance site i18n — one language, everywhere.
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
    { code: "en",    name: "English",        dir: "ltr", flag: "🇬🇧" },
    { code: "de",    name: "Deutsch",        dir: "ltr", flag: "🇩🇪" },
    { code: "it",    name: "Italiano",       dir: "ltr", flag: "🇮🇹" },
    { code: "ur",    name: "اردو",           dir: "rtl", flag: "🇵🇰" },
    { code: "pt-BR", name: "Português (BR)", dir: "ltr", flag: "🇧🇷" },
    { code: "vi",    name: "Tiếng Việt",     dir: "ltr", flag: "🇻🇳" },
    { code: "ar",    name: "عربي",           dir: "rtl", flag: "🇵🇸" },
    { code: "es",    name: "Español",        dir: "ltr", flag: "🇪🇸" },
    { code: "zh",    name: "中文",           dir: "ltr", flag: "🇨🇳" }
  ];
  var STORE = "welance-lang";
  var dicts = {};
  var current = "en";
  var warned = {};
  // These operational/security claims changed in 1.10.0. Until each native
  // translation is re-reviewed, keep the current English source instead of
  // showing a fluent but false pre-1.10 claim in another language.
  var NEEDS_RETRANSLATION = {
    "index.p5": true,
    "index.p10": true,
    "int.r1.p": true,
    "data.r1.a": true,
    "data.byok": true,
    "data.limits": true,
    "sec.w2.a": true,
    "sec.limit2": true,
    "sec.do2": true,
    "rules.p6": true,
    "calc.note": true
  };

  function meta(code) {
    return LANGS.filter(function (l) { return l.code === code; })[0] || null;
  }

  function register(code, dict) { dicts[code] = dict; }

  function t(key) {
    if (current !== "en" && NEEDS_RETRANSLATION[key]) return null;
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

  // A closed <select> shows the text of the option that is selected, and on a
  // phone "🇧🇷 Português (BR)" does not fit beside everything else in the
  // header. Only the chosen one is shortened, so the list you open still names
  // every language in full — a language you cannot read is one you cannot pick.
  // the same width at which the header drops its nav: from there down, every
  // pixel is spoken for
  var narrow = window.matchMedia("(max-width: 900px)");
  var tiny = window.matchMedia("(max-width: 400px)");

  function renderSwitcher() {
    var host = document.getElementById("langswitch");
    if (!host) return;
    host.textContent = "";
    var sel = document.createElement("select");
    sel.className = "wl-lang-select";
    sel.setAttribute("aria-label", "language");
    LANGS.forEach(function (l) {
      var o = document.createElement("option");
      o.value = l.code;
      var d = dicts[l.code];
      var draft = l.code !== "en" && d && d.reviewed === false;
      var chosen = l.code === current;
      o.textContent = chosen && tiny.matches
        ? l.flag
        : chosen && narrow.matches
          ? l.flag + " " + l.code.split("-")[0].toUpperCase()
          : l.flag + " " + l.name + (draft ? " · draft" : "");
      o.setAttribute("aria-label", l.name);
      if (draft) o.title = "machine-drafted — awaiting native-speaker review";
      if (l.code === current) o.selected = true;
      sel.appendChild(o);
    });
    sel.addEventListener("change", function () { set(sel.value); });
    host.appendChild(sel);
  }

  // crossing the width where the short label starts or stops making sense
  if (narrow.addEventListener) {
    narrow.addEventListener("change", renderSwitcher);
    tiny.addEventListener("change", renderSwitcher);
  }

  function set(code, guessed) {
    if (!meta(code)) code = "en";
    current = code;
    try { localStorage.setItem(STORE, code); } catch (e) {}
    // The address follows the choice, so a page can be shared as it was read.
    // A guess is not a choice: a browser's Accept-Language must never end up
    // in a URL someone then sends to somebody else.
    try {
      var want = guessed ? null : pathFor(code);
      if (want && want !== location.pathname + location.search + location.hash) {
        history.replaceState(null, "", want);
      }
    } catch (e) {}
    var m = meta(code);
    document.documentElement.setAttribute("lang", code);
    document.documentElement.setAttribute("dir", m.dir);
    applyNodes();
    renderSwitcher();
    document.dispatchEvent(new CustomEvent("welance:lang", { detail: { lang: code, dir: m.dir } }));
  }

  /* Which language to show, in order of authority:
       1. ?lang= — an explicit, shareable choice
       2. what this visitor picked before
       3. what their browser asks for
       4. English
     Never a redirect. The English markup is the content of record and the only
     URL search engines see; translation happens in the page, so there are no
     duplicate URLs to index and nothing to get wrong with hreflang. */
  function fromBrowser() {
    var wanted = (navigator.languages && navigator.languages.length
      ? navigator.languages : [navigator.language || ""]);
    for (var i = 0; i < wanted.length; i++) {
      var tag = String(wanted[i]);
      if (meta(tag)) return tag;                       // exact: pt-BR
      var base = tag.split("-")[0];
      if (meta(base)) return base;                     // de-AT → de
      var regional = LANGS.filter(function (l) {       // pt-PT → pt-BR
        return l.code.split("-")[0] === base;
      })[0];
      if (regional) return regional.code;
    }
    return null;
  }

  /* /it/rules.html — the language is part of the address.
     English keeps the bare paths: it is the content of record, the copy every
     translation is made from, and giving it a prefix of its own would move
     every existing URL for nothing. */
  function fromPath() {
    var first = location.pathname.split("/")[1];
    return first && meta(first) ? first : null;
  }

  function pathFor(code) {
    var rest = location.pathname.replace(/^\/[^/]+/, function (m) {
      return meta(m.slice(1)) ? "" : m;
    });
    return (code === "en" ? "" : "/" + code) + (rest || "/") + location.search + location.hash;
  }

  function initial() {
    try {
      var q = new URLSearchParams(location.search).get("lang");
      if (q && meta(q)) return q;
      var routed = fromPath();
      if (routed) return routed;
      var stored = localStorage.getItem(STORE);
      if (stored && meta(stored)) return stored;
      var guess = fromBrowser();
      if (guess) return guess;
    } catch (e) {}
    return "en";
  }

  root.WelanceI18n = {
    LANGS: LANGS, STORE: STORE, pathFor: pathFor,
    register: register, t: t, set: set,
    mountSwitcher: renderSwitcher, // chrome.js re-mounts after re-rendering the header
    get lang() { return current; },
    get dir() { return (meta(current) || LANGS[0]).dir; }
  };

  function boot() {
    var lang = initial();
    var guessed = false;
    try {
      guessed = !new URLSearchParams(location.search).get("lang") &&
        !fromPath() && !localStorage.getItem(STORE);
    } catch (e) {}
    set(lang, guessed);
    // a guess is a courtesy, not a decision: only remember what a human picks
    if (guessed) { try { localStorage.removeItem(STORE); } catch (e) {} }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof self !== "undefined" ? self : globalThis);
