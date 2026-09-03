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

  /* Keep the header about things visitors can do. */
  var NAV = [
    { href: "integrate.html", key: "chrome.integrate", en: "Integrate" }
  ];

  // the footer's second column: the things a builder looks for
  var BUILD = [
    { href: "integrate.html", key: "chrome.integrate", en: "Integrate" },
    { href: "console.html",   key: "chrome.console",   en: "Console" },
    { href: "rules.html",     key: "chrome.rules",     en: "Rules" },
    { href: "/docs",          key: "chrome.api",       en: "API docs" },
    { href: "llms.txt",       key: "chrome.llms",      en: "llms.txt" },
    { href: "data.html",      key: "chrome.data",      en: "Your brief, your key" },
    { href: "https://github.com/welance/perfect-brief", key: "chrome.github", en: "GitHub", icon: true }
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

  /* The lockup, the Directory's: two static marks, not one animated one.
     Paths are welance/directory's own assets/images/weLogo.svg and
     welanceLogo.svg, verbatim. */
  var MARK =
    '<svg class="wl-ast" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 30" fill="none" aria-hidden="true">' +
    '<path fill-rule="evenodd" clip-rule="evenodd" d="M18.4027 16.5L26.3542 24.546L24.2578 26.6673L16.3062 18.6213V30H13.3415V18.6213L5.38992 26.6673L3.29351 24.546L11.245 16.5H0L0 13.5H11.2451L3.29369 5.45412L5.3901 3.3328L13.3415 11.3786V0L16.3062 0V11.3786L24.2576 3.3328L26.354 5.45412L18.4026 13.5H29.6477V16.5H18.4027Z" fill="currentColor"/>' +
    "</svg>";

  var WORDMARK =
    '<svg class="wl-logo" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 112 24" fill="none" aria-hidden="true">' +
    '<path d="M4.20297 23.1771H7.08848L11.3712 10.5582H11.4319L15.745 23.1771H18.6305L22.4272 6.94404H19.481L16.8385 18.8585H16.7777L12.738 6.94404H10.0955L6.05577 18.8585H5.99502L3.3525 6.94404H0.40625L4.20297 23.1771Z" fill="currentColor"/>' +
    '<path d="M23.734 15.0606C23.734 20.1755 26.7714 23.6365 31.2363 23.6365C34.3041 23.6365 36.6732 22.2583 38.1008 19.563L35.7924 18.0009C34.4559 20.1755 33.241 20.9719 31.2059 20.9719C29.8999 20.9719 28.8368 20.5124 28.0167 19.563C27.1966 18.6135 26.7714 17.3883 26.741 15.9488H38.4956V14.693C38.4956 9.82312 35.5798 6.48462 31.2059 6.48462C26.8018 6.48462 23.734 10.0069 23.734 15.0606ZM26.8018 13.6517C26.8625 11.2014 28.776 9.14929 31.2059 9.14929C33.7573 9.14929 35.4279 10.987 35.5494 13.6517H26.8018Z" fill="currentColor"/>' +
    '<path d="M41.6047 23.1771H44.5813V0.818359H41.6047V23.1771Z" fill="currentColor"/>' +
    '<path d="M47.7022 18.9504C47.7022 21.7988 49.798 23.6365 52.9872 23.6365C54.9615 23.6365 56.6321 22.8708 57.5129 21.6151H57.5737V23.1771H60.3073V12.0284C60.3073 8.59798 57.9989 6.48462 54.2629 6.48462C52.5316 6.48462 51.0433 6.97467 49.8284 7.92415C48.6438 8.87364 47.9148 10.1294 47.6415 11.7221L50.527 12.3346C50.9218 10.2825 52.2887 9.11866 54.2629 9.11866C56.0854 9.11866 57.2092 9.97626 57.2092 11.2933C57.2092 12.4878 56.298 13.0697 53.3821 13.8048C49.2817 14.7849 47.7022 16.2245 47.7022 18.9504ZM57.3611 17.6946C57.3611 19.563 55.6905 20.9412 53.3517 20.9412C51.5597 20.9412 50.6181 20.1449 50.6181 18.7666C50.6181 17.5415 51.5901 16.837 54.1415 16.1938C56.0854 15.6731 57.027 15.1831 57.3003 14.4786H57.3611V17.6946Z" fill="currentColor"/>' +
    '<path d="M63.8511 23.1771H66.8277V13.1616C66.8277 10.8339 68.3464 9.27181 70.6548 9.27181C72.9632 9.27181 74.33 10.742 74.33 13.1616V23.1771H77.3067V12.7022C77.3067 8.90427 74.9071 6.48462 71.2319 6.48462C69.531 6.48462 67.7389 7.25033 66.767 8.38358H66.7062V6.94404H63.8511V23.1771Z" fill="currentColor"/>' +
    '<path d="M80.2399 15.0606C80.2399 20.1449 83.338 23.6365 87.8029 23.6365C89.6557 23.6365 91.2352 23.1159 92.5108 22.0439C93.8169 20.9719 94.6066 19.5017 94.88 17.6946L92.0249 17.1127C91.5693 19.5323 90.081 20.8494 87.8029 20.8494C85.0085 20.8494 83.2165 18.6135 83.2165 15.0606C83.2165 11.5077 85.0085 9.27181 87.8029 9.27181C90.081 9.27181 91.63 10.6501 92.0249 13.0085L94.88 12.4265C94.6066 10.6195 93.8169 9.17992 92.5108 8.10792C91.2352 7.03593 89.6557 6.48462 87.8029 6.48462C83.338 6.48462 80.2399 9.97626 80.2399 15.0606Z" fill="currentColor"/>' +
    '<path d="M97.2064 15.0606C97.2064 20.1755 100.244 23.6365 104.709 23.6365C107.777 23.6365 110.146 22.2583 111.573 19.563L109.265 18.0009C107.928 20.1755 106.713 20.9719 104.678 20.9719C103.372 20.9719 102.309 20.5124 101.489 19.563C100.669 18.6135 100.244 17.3883 100.213 15.9488H111.968V14.693C111.968 9.82312 109.052 6.48462 104.678 6.48462C100.274 6.48462 97.2064 10.0069 97.2064 15.0606ZM100.274 13.6517C100.335 11.2014 102.248 9.14929 104.678 9.14929C107.23 9.14929 108.9 10.987 109.022 13.6517H100.274Z" fill="currentColor"/>' +
    "</svg>";

  /* the welance asterisk alone — path verbatim from welance.com's footer */
  var ASTERISK =
    '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 30 30" class="wl-asterisk" aria-hidden="true">' +
    '<path fill="currentColor" fill-rule="evenodd" d="m18.403 16.5 7.951 8.046-2.096 2.121-7.952-8.046V30h-2.965V18.621L5.39 26.667l-2.096-2.121 7.951-8.046H0v-3h11.245L3.294 5.454 5.39 3.333l7.952 8.046V0h2.964v11.379l7.952-8.046 2.096 2.121-7.951 8.046h11.245v3z" clip-rule="evenodd"></path></svg>';

  /* Two lockups, on purpose.
     The header wears ✳ brief bar_ — the asterisk without the wordmark.
     The ruleset is MIT and meant to be common property; a header that
     co-brands it every time you load a page argues the opposite. The mark
     stays because it recurs anyway (the colour rule, the footer), so the
     pages still read as welance work without saying so twice a screen.
     The footer wears the full ✳ welance / brief bar_ — provenance
     belongs where you go looking for it. */
  function lockupHead() {
    return '<a class="wl-brandline" href="./" aria-label="brief bar">' +
      MARK + '<span class="wl-project"><span class="name">' +
      tt("chrome.slash", "brief bar") + '<span class="b">_</span></span></span></a>';
  }

  function lockupFoot() {
    // the footer names the project, not the maintainer: welance is one line
    // in the "maintained by" column, the way any OSS project credits one
    return '<a class="wl-foot-lock" href="./" aria-label="brief bar">' +
      MARK +
      '<span class="wl-project">' +
      '<span class="name">' + tt("chrome.slash", "brief bar") +
      '<span class="b">_</span></span></span></a>';
  }

  /* the welance colour rule: five bars, full width, flush under the header.
     Full weight on the landing page; thinner everywhere else, where it is
     chrome rather than part of the page. */
  function rule() {
    var thin = current() === "index.html" ? "" : " is-thin";
    return '<div class="wl-rule' + thin + '" aria-hidden="true">' +
      '<i style="background:var(--wl-c)"></i>' +
      '<i style="background:var(--wl-y)"></i>' +
      '<i style="background:var(--wl-cy)"></i>' +
      '<i style="background:var(--wl-p)"></i>' +
      '<i style="background:var(--wl-b)"></i></div>';
  }

  function renderHeader() {
    var host = document.getElementById("site-header");
    if (!host) return;
    var here = current();
    var nav = NAV.map(function (p) {
      var active = p.href === here ? ' aria-current="page"' : "";
      return '<a class="wl-nav-item" href="' + p.href + '"' + active + ">" +
        tt(p.key, p.en) + "</a>";
    }).join("");
    host.innerHTML =
      '<div class="wl-head"><div class="wl-head-in">' +
      lockupHead() +
      // the quiet line leads the right-hand group, as it does on the
      // Directory: status, then where to go, then the one way out
      '<span class="wl-status" id="wl-release">© 2011–2026 · live</span>' +
      '<nav class="wl-nav" aria-label="Main">' + nav + "</nav>" +
      '<div class="wl-head-right">' +
      (host.hasAttribute("data-own-lang") ? "" : '<nav id="langswitch" aria-label="language"></nav>') +
      '<a class="wl-src" href="https://github.com/welance/perfect-brief" ' +
        'aria-label="' + tt("chrome.source", "the source on GitHub") + '" ' +
        'title="' + tt("chrome.source", "the source on GitHub") + '">' + GH + "</a>" +
      // Not a call to action: a destination, named. It used to be a filled
      // pill saying "Find a team", which is this site asking you for
      // something. The site's job is the ruleset; the Directory is one
      // place that runs it, and saying so quietly is the honest size of
      // the claim. The name is a proper noun, so it is not translated.
      '<a class="wl-out" href="https://welance.com/directory" ' +
        'title="' + tt("chrome.outTitle", "the noticeboard that runs this ruleset") + '">' +
        'welance/Directory <span aria-hidden="true">↗</span></a>' +
      '<button class="wl-burger" type="button" aria-expanded="false" aria-controls="wl-menu" ' +
        'aria-label="' + tt("chrome.menu", "menu") + '">' +
        '<span></span><span></span><span></span></button>' +
      "</div></div>" +
      rule() +
      // the same pages the footer lists: on a phone the header cannot show
      // them, but it must still be able to reach them
      '<nav class="wl-menu" id="wl-menu" hidden aria-label="' + tt("chrome.menu", "menu") + '">' +
      '<div class="wl-menu-in">' +
      '<div class="wl-menu-lang" id="wl-menu-lang"></div>' +
      '<div class="wl-menu-col"><p class="wl-menu-h">' + tt("chrome.build", "Build with it") + "</p>" +
      menuCol(BUILD) + "</div>" +
      "</div></nav>" +
      "</div>";
    if (window.WelanceI18n && window.WelanceI18n.mountSwitcher) window.WelanceI18n.mountSwitcher();
    loadRelease();
    wireMenu(host);
  }

  var releaseVersion = null;
  var releaseRequest = null;
  function paintRelease() {
    var el = document.getElementById("wl-release");
    if (!el) return;
    el.textContent = "© 2011–2026" + (releaseVersion ? " · v" + releaseVersion : "") + " · live";
  }
  function loadRelease() {
    paintRelease();
    if (releaseVersion || releaseRequest || !window.fetch) return;
    releaseRequest = fetch("/v1/healthz", { headers: { accept: "application/json" } })
      .then(function (res) { return res.ok ? res.json() : null; })
      .then(function (body) {
        if (body && /^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$/.test(body.release_version || "")) {
          releaseVersion = body.release_version;
          paintRelease();
        }
      })
      .catch(function () {})
      .then(function () { releaseRequest = null; });
  }

  function menuCol(items) {
    var here = current();
    return items.map(function (p) {
      var on = p.href === here ? ' aria-current="page"' : "";
      return '<a href="' + p.href + '"' + on + ">" + (p.icon ? GH : "") + tt(p.key, p.en) + "</a>";
    }).join("");
  }

  /* The phone's way through the site. It closes on Escape, on a click outside,
     and as soon as the window is wide enough to show the nav again — a panel
     left open behind a visible menu is a puzzle nobody asked for. */
  function wireMenu(host) {
    var btn = host.querySelector(".wl-burger");
    var panel = host.querySelector(".wl-menu");
    if (!btn || !panel) return;

    /* On a phone the language switch moves into the panel rather than being
       duplicated there: one element, one id, one mounted switcher — and the
       header bar gets its width back for the CTA, which in Spanish needs it. */
    var sw = document.getElementById("langswitch");
    var slot = panel.querySelector("#wl-menu-lang");
    var bar = host.querySelector(".wl-head-right");
    var src = host.querySelector(".wl-src");
    var small = window.matchMedia("(max-width: 560px)");
    function place() {
      if (!sw || !slot || !bar) return;
      if (small.matches) { if (sw.parentNode !== slot) slot.appendChild(sw); }
      else if (sw.parentNode !== bar) bar.insertBefore(sw, src || bar.firstChild);
    }
    place();
    if (small.addEventListener) small.addEventListener("change", place);

    function shut() {
      panel.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    }
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = btn.getAttribute("aria-expanded") === "true";
      panel.hidden = open;
      btn.setAttribute("aria-expanded", open ? "false" : "true");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") shut();
    });
    document.addEventListener("click", function (e) {
      if (!panel.hidden && !panel.contains(e.target)) shut();
    });
    if (window.matchMedia) {
      var wide = window.matchMedia("(min-width: 901px)");
      if (wide.addEventListener) wide.addEventListener("change", shut);
    }
  }

  /* Light or dark, remembered. The system preference decides until someone
     says otherwise; then their choice wins, on every page. */
  function wireTheme(host) {
    var btn = host.querySelector(".wl-theme");
    if (!btn) return;
    var SUN = '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="4"/>' +
      '<g stroke="currentColor" stroke-width="1.6" stroke-linecap="round">' +
      '<path d="M10 1v2M10 17v2M1 10h2M17 10h2M3.6 3.6l1.4 1.4M15 15l1.4 1.4M16.4 3.6L15 5M5 15l-1.4 1.4"/></g></svg>';
    var MOON = '<svg viewBox="0 0 20 20" aria-hidden="true">' +
      '<path d="M16 12.2A7 7 0 0 1 7.8 4a7 7 0 1 0 8.2 8.2z"/></svg>';
    var paint = function () {
      btn.innerHTML = document.documentElement.getAttribute("data-theme") === "dark" ? SUN : MOON;
    };
    paint();
    btn.addEventListener("click", function () {
      var now = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", now);
      try { localStorage.setItem("welance-theme", now); } catch (e) {}
      paint();
    });
  }

  var GH = '<svg class="wl-gh" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.5 7.5 0 0 1 2-.27c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>';

  /* The three doors in. They used to be three links among twelve; given a
     line of their own each, they are findable. */
  var STARTS = [
    { href: "console.html", key: "chrome.ctaBrief", en: "Score a brief",
      subKey: "chrome.startBriefSub", subEn: "Against the fourteen public rules, in the browser" },
    // named and described, not offered — the ruleset does not belong to the
    // one noticeboard that happens to run it
    { href: "https://welance.com/directory", key: "chrome.startDirectory", en: "welance/Directory",
      subKey: "chrome.startDirectorySub",
      subEn: "One noticeboard that runs this ruleset. Briefs stay blind until a team takes one." }
  ];

  function renderFooter() {
    var host = document.getElementById("site-footer");
    if (!host) return;
    var col = function (items) {
      return items.map(function (p) {
        var cls = p.icon ? "wl-foot-link wl-foot-gh" : "wl-foot-link";
        return '<a class="' + cls + '" href="' + p.href + '">' +
          (p.icon ? GH : "") + tt(p.key, p.en) + "</a>";
      }).join("");
    };
    var starts = STARTS.map(function (s) {
      return '<a class="wl-foot-start" href="' + s.href + '">' +
        '<span class="wl-foot-start-t">' + tt(s.key, s.en) + "</span>" +
        '<span class="wl-foot-start-s">' + tt(s.subKey, s.subEn) + "</span></a>";
    }).join("");
    host.innerHTML =
      '<footer class="wl-foot">' +
      // the blue half of the two-tone close: two doors on the brand's
      // second voice, sitting directly on the ink band below
      '<section class="wl-close">' +
      '<div class="wl-close-ast" aria-hidden="true">' + ASTERISK + "</div>" +
      '<div class="wl-close-in"><div>' +
      '<p class="eyebrow">' + tt("chrome.closeEyebrow", "the ruleset, not the service") + "</p>" +
      // The heading used to be "The team your goal deserves" — an agency
      // promise on a page whose whole argument is that the bar belongs to
      // everyone. It says what the thing is instead. (New key: the old one
      // is translated into eight languages and would keep saying the old
      // sentence on those pages.)
      '<h2 class="h1">' + tt("chrome.closeHead", "Fourteen rules. Yours to run, or to change") + '<span class="b">_</span></h2>' +
      '<p class="wl-close-note">' + tt("chrome.closeNote",
        "welance wrote it and runs one noticeboard on it. The rules are MIT — " +
        "fork them, argue with them, run your own.") + "</p>" +
      "</div>" +
      '<div class="wl-close-row">' +
      '<a class="btn accent lg" href="console.html">' + tt("chrome.ctaBrief", "Score a brief") + "</a>" +
      '<a class="btn lg" href="rules.html">' + tt("chrome.closeRules", "Read the rules") + "</a>" +
      "</div></div></section>" +
      // the ink half: a discovery surface — every page linked, the open
      // ruleset with its GitHub home, who operates it, the legal line
      '<div class="wl-foot-deep"><div class="wl-foot-in">' +
      '<div class="wl-foot-grid">' +
      '<div class="wl-foot-brand">' + lockupFoot() +
      '<p class="wl-foot-blurb">' + tt("chrome.blurb",
        "An open ruleset for checking digital product briefs. Fourteen public rules, " +
        "four hard requirements, code that owns every number. MIT: fork it, change it, run it.") + "</p>" +
      '<p class="mono-sm wl-foot-contact">' + tt("chrome.contact",
        "hello@welance.com") + "</p></div>" +
      '<nav class="wl-foot-col" aria-label="' + tt("chrome.colStart", "Start here") + '">' +
      '<p class="mono-sm wl-foot-k">' + tt("chrome.colStart", "Start here") + "</p>" +
      starts + "</nav>" +
      '<nav class="wl-foot-col" aria-label="' + tt("chrome.build", "Build with it") + '">' +
      '<p class="mono-sm wl-foot-k">' + tt("chrome.build", "Build with it") + "</p>" +
      col(BUILD) + "</nav>" +
      '<div class="wl-foot-col">' +
      '<p class="mono-sm wl-foot-k">' + tt("chrome.colMaintained", "Maintained by") + "</p>" +
      '<p class="wl-foot-op">' + tt("chrome.maintainedBy",
        "welance, a collective of independent senior teams, wrote this bar and hosts it. " +
        "Anyone can use it, change it or run their own.") + "</p>" +
      '<a class="wl-foot-link" href="https://welance.com/directory">' + tt("chrome.directoryAd",
        "Need a team for your brief? welance/Directory ↗") + "</a>" +
      "</div></div>" +
      '<div class="wl-foot-legal mono-sm"><p>' + tt("chrome.legal", "© 2011–2026 welance · MIT") + "</p>" +
      '<nav><button class="wl-theme" type="button" aria-label="' +
        tt("chrome.theme", "light or dark") + '"></button>' +
      '<a href="https://welance.com/imprint">' + tt("chrome.imprint", "Imprint") + "</a>" +
      '<a href="https://welance.com/privacy">' + tt("chrome.privacy", "Privacy") + "</a>" +
      '<a href="https://otto.welance.com" rel="nofollow" target="_blank">' + tt("chrome.login", "Login") + "</a></nav></div>" +
      "</div></div></footer>";
    wireTheme(host);
  }

  function render() { renderHeader(); renderFooter(); }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
  document.addEventListener("welance:lang", render);
})();
