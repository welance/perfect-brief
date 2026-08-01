/* welance site chrome — the shared header and footer, copied from
 * welance.com's own (logo left, semibold menu + pill button right; footer
 * with the asterisk, the two offices, and the Imprint | Login line).
 *
 * Pages opt in with <div id="site-header"></div> and
 * <div id="site-footer"></div>. Labels translate through WelanceI18n when
 * it is present (chrome.* keys), falling back to the English literals here.
 * A page that already has its own language control (price, console) sets
 * data-own-lang on the header mount and the chrome skips rendering one.
 * No dependencies, no build step — same contract as i18n.js.
 */
(function () {
  "use strict";

  var PAGES = [
    { href: "method.html", key: "chrome.method", en: "The method" },
    { href: "index.html",  key: "chrome.brief",  en: "Perfect Brief" },
    { href: "price.html",  key: "chrome.price",  en: "Perfect Price" },
    { href: "team.html",   key: "chrome.team",   en: "Perfect Team" }
  ];
  var EXTRA = [
    { href: "console.html", key: "chrome.console", en: "Console" },
    { href: "rules.html",   key: "chrome.rules",   en: "Rules" },
    { href: "https://github.com/welance/perfect-brief", key: "chrome.github", en: "GitHub" }
  ];

  function tt(key, en) {
    var I = window.WelanceI18n;
    if (!I) return en;
    var v = I.t(key);
    return v === null || v === undefined ? en : v;
  }

  function current() {
    var p = location.pathname.split("/").pop() || "index.html";
    return p === "" ? "index.html" : p;
  }

  /* the welance wordmark — asterisk + name, paths verbatim from welance.com */
  var LOGO =
    '<svg class="wl-logo animated" xmlns="http://www.w3.org/2000/svg" viewBox="26 68 108 26" preserveAspectRatio="xMidYMid meet" role="img" aria-label="welance">' +
    '<g transform="matrix(0.0833,0,0,0.0833,17.675,60.675)"><g transform="translate(749.325 232)" fill="none" stroke="currentColor" stroke-width="26">' +
    '<path class="wl-stroke wl-s1" d="M-374.25,22 L-622.25,22"/><path class="wl-stroke wl-s2" d="M-498.25,-102 L-498.25,146"/>' +
    '<path class="wl-stroke wl-s3" d="M-410.5,109.75 L-586,-65.75"/><path class="wl-stroke wl-s4" d="M-586,109.75 L-410.5,-65.75"/></g></g>' +
    '<g class="wl-glyph wl-g1" transform="matrix(0.0833,0,0,0.0833,61.3753,82.5643)"><path fill="currentColor" d="M-60.793,67.637 L-36.475,67.637 L-0.384,-37.519 L0.128,-37.519 L36.475,67.637 L60.793,67.637 L92.788,-67.637 L67.96,-67.637 L45.691,31.65 L45.178,31.65 L11.134,-67.637 L-11.134,-67.637 L-45.178,31.65 L-45.69,31.65 L-67.96,-67.637 L-92.788,-67.637 Z"/></g>' +
    '<g class="wl-glyph wl-g2" transform="matrix(0.0833,0,0,0.0833,80.0057,79.9957)"><path fill="currentColor" d="M-119.854,30.837 C-119.854,73.461 -94.257,102.303 -56.63,102.303 C-30.777,102.303 -10.811,90.817 1.219,68.357 L-18.234,55.339 C-29.497,73.461 -39.736,80.097 -56.885,80.097 C-67.892,80.097 -76.851,76.269 -83.762,68.357 C-90.673,60.444 -94.257,50.235 -94.513,38.239 L4.547,38.239 L4.547,27.774 C4.547,-12.809 -20.026,-40.63 -56.885,-40.63 C-94.001,-40.63 -119.854,-11.277 -119.854,30.837 Z M-94.001,19.096 C-93.489,-1.323 -77.363,-18.424 -56.885,-18.424 C-35.384,-18.424 -21.306,-3.11 -20.282,19.096 Z"/></g>' +
    '<g class="wl-glyph wl-g3" transform="matrix(0.0833,0,0,0.0833,83.6117,80.4382)"><path fill="currentColor" d="M-12.541,93.161 L12.541,93.161 L12.541,-93.161 L-12.541,-93.161 Z"/></g>' +
    '<g class="wl-glyph wl-g4" transform="matrix(0.0833,0,0,0.0833,80.0057,79.9957)"><path fill="currentColor" d="M82.13,63.252 C82.13,86.989 99.8,102.303 126.67,102.303 C143.31,102.303 157.39,95.922 164.81,85.457 L165.32,85.457 L165.32,98.474 L188.36,98.474 L188.36,5.568 C188.36,-23.018 168.91,-40.63 137.42,-40.63 C122.83,-40.63 110.29,-36.546 100.05,-28.634 C90.07,-20.721 83.93,-10.256 81.62,3.016 L105.94,8.121 C109.27,-8.98 120.78,-18.679 137.42,-18.679 C152.78,-18.679 162.25,-11.533 162.25,-0.557 C162.25,9.397 154.57,14.246 130,20.372 C95.44,28.54 82.13,40.536 82.13,63.252 Z M163.53,52.787 C163.53,68.357 149.45,79.842 129.74,79.842 C114.64,79.842 106.71,73.206 106.71,61.72 C106.71,51.511 114.9,45.64 136.4,40.28 C152.78,35.941 160.72,31.858 163.02,25.987 L163.53,25.987 Z"/></g>' +
    '<g class="wl-glyph wl-g5" transform="matrix(0.0833,0,0,0.0833,102.9065,82.4049)"><path fill="currentColor" d="M-56.7,69.552 L-31.61,69.552 L-31.61,-13.91 C-31.61,-33.308 -18.81,-46.325 0.64,-46.325 C20.1,-46.325 31.61,-34.074 31.61,-13.91 L31.61,69.552 L56.7,69.552 L56.7,-17.739 C56.7,-49.388 36.48,-69.552 5.5,-69.552 C-8.83,-69.552 -23.93,-63.171 -32.12,-53.727 L-32.63,-53.727 L-32.63,-65.723 L-56.7,-65.723 Z"/></g>' +
    '<g class="wl-glyph wl-g6" transform="matrix(0.0833,0,0,0.0833,114.8272,82.5643)"><path fill="currentColor" d="M-61.685,0 C-61.685,42.369 -35.575,71.466 2.045,71.466 C17.665,71.466 30.975,67.128 41.725,58.195 C52.735,49.261 59.385,37.01 61.685,21.951 L37.625,17.102 C33.785,37.265 21.245,48.24 2.045,48.24 C-21.505,48.24 -36.605,29.607 -36.605,0 C-36.605,-29.608 -21.505,-48.24 2.045,-48.24 C21.245,-48.24 34.305,-36.753 37.625,-17.1 L61.685,-21.951 C59.385,-37.01 52.735,-49.005 41.725,-57.938 C30.975,-66.871 17.665,-71.466 2.045,-71.466 C-35.575,-71.466 -61.685,-42.37 -61.685,0 Z"/></g>' +
    '<g class="wl-glyph wl-g7" transform="matrix(0.0833,0,0,0.0833,80.0057,79.9957)"><path fill="currentColor" d="M499.32,30.837 C499.32,73.461 524.92,102.303 562.54,102.303 C588.4,102.303 608.36,90.817 620.39,68.357 L600.94,55.339 C589.68,73.461 579.44,80.097 562.29,80.097 C551.28,80.097 542.32,76.269 535.41,68.357 C528.5,60.444 524.92,50.235 524.66,38.239 L623.72,38.239 L623.72,27.774 C623.72,-12.809 599.15,-40.63 562.29,-40.63 C525.17,-40.63 499.32,-11.277 499.32,30.837 Z M525.17,19.096 C525.68,-1.323 541.81,-18.424 562.29,-18.424 C583.79,-18.424 597.87,-3.11 598.89,19.096 Z"/></g></svg>';

  /* the welance asterisk alone — path verbatim from welance.com's footer */
  var ASTERISK =
    '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 30 30" class="wl-asterisk" aria-hidden="true">' +
    '<path fill="currentColor" fill-rule="evenodd" d="m18.403 16.5 7.951 8.046-2.096 2.121-7.952-8.046V30h-2.965V18.621L5.39 26.667l-2.096-2.121 7.951-8.046H0v-3h11.245L3.294 5.454 5.39 3.333l7.952 8.046V0h2.964v11.379l7.952-8.046 2.096 2.121-7.951 8.046h11.245v3z" clip-rule="evenodd"></path></svg>';

  function renderHeader() {
    var host = document.getElementById("site-header");
    if (!host) return;
    var here = current();
    var nav = PAGES.map(function (p) {
      var active = p.href === here ? ' aria-current="page"' : "";
      return '<a class="wl-nav-item" href="' + p.href + '"' + active + ">" +
        tt(p.key, p.en) + "</a>";
    }).join("");
    host.innerHTML =
      '<div class="wl-head"><div class="wl-head-in">' +
      '<a class="wl-head-logo" href="./" aria-label="welance — home">' + LOGO + "</a>" +
      '<nav class="wl-nav" aria-label="Main">' + nav + "</nav>" +
      '<div class="wl-head-right">' +
      (host.hasAttribute("data-own-lang") ? "" : '<nav id="langswitch" aria-label="language"></nav>') +
      '<a class="wl-pill" href="https://welance.com">welance.com</a>' +
      "</div></div></div>";
    if (window.WelanceI18n && window.WelanceI18n.mountSwitcher) window.WelanceI18n.mountSwitcher();
  }

  function renderFooter() {
    var host = document.getElementById("site-footer");
    if (!host) return;
    var links = PAGES.concat(EXTRA).map(function (p) {
      return '<a href="' + p.href + '">' + tt(p.key, p.en) + "</a>";
    }).join("");
    host.innerHTML =
      '<footer class="wl-foot"><div class="wl-foot-in">' +
      '<div class="wl-foot-top">' +
      '<div class="wl-foot-mark">' + ASTERISK + "</div>" +
      '<div class="wl-foot-offices">' +
      '<div class="wl-office"><p class="wl-office-h">🏙️ welance Berlin</p>' +
      "<p>Moosdorfstraße 7-9,<br>12435 Berlin</p>" +
      '<a href="tel:+493060985775">t: +49 30 60 98 57 75</a>' +
      '<a href="mailto:hello@welance.com">m: hello@welance.com</a></div>' +
      '<div class="wl-office"><p class="wl-office-h">🌳 welance Italia</p>' +
      "<p>Via San Michele 18,<br>12050 Lequio Berria (CN)</p>" +
      '<a href="tel:+393475331532">t: +39 347 533 1532</a>' +
      '<a href="mailto:ciao@welance.com">m: ciao@welance.com</a></div></div>' +
      '<div class="wl-foot-links"><p class="wl-office-h">' + tt("chrome.links", "The method, open") + "</p>" + links + "</div>" +
      "</div>" +
      '<div class="wl-foot-bottom"><p>© 2026 · MIT</p>' +
      '<nav><a href="https://welance.com/imprint">' + tt("chrome.imprint", "Imprint") + "</a><span>|</span>" +
      '<a href="https://otto.welance.com" rel="nofollow" target="_blank">' + tt("chrome.login", "Login") + "</a></nav></div>" +
      "</div></footer>";
  }

  function render() { renderHeader(); renderFooter(); }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
  document.addEventListener("welance:lang", render);
})();
