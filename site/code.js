/* Code blocks: language tabs, one-click copy, and a small honest highlighter.
 *
 * Why not highlight.js or Shiki: this site has no build step and makes a point
 * of being readable in view-source. Two hundred lines of regex we can read
 * beats a 300kB dependency we cannot. The markup stays plain text — the
 * highlighting is applied at runtime, so "copy" always yields clean code.
 *
 * Markup contract:
 *   <div class="code">
 *     <div class="code-bar">…tabs…<button class="code-copy"></button></div>
 *     <pre data-lang="bash" data-tab="curl">…plain text…</pre>
 *     <pre data-lang="json" hidden>…</pre>
 *   </div>
 */
(function () {
  "use strict";

  // Keywords worth colouring, per language. Deliberately short: the point is
  // legibility, not a full grammar.
  var KEYWORDS = {
    js: "const|let|var|await|async|function|return|new|import|from|export|true|false|null",
    py: "import|from|def|return|with|as|if|else|for|in|True|False|None",
    bash: "curl|export|echo",
    json: "true|false|null",
  };

  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /* Tokenise, then escape exactly once — both the tokens and the gaps between
     them. The input is our own page text, never user input, but escaping is
     what makes that guarantee visible instead of assumed. */
  function highlight(code, lang) {
    var kw = KEYWORDS[lang] || "";
    var re = new RegExp(
      "(\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^'\\\\]|\\\\.)*'|`(?:[^`\\\\]|\\\\.)*`)" + // 1 strings
      "|(#[^\\n]*|//[^\\n]*)" +                                                       // 2 comments
      "|(https?://[^\\s'\"]+)" +                                                       // 3 urls
      "|(\\s-{1,2}[A-Za-z][\\w-]*)" +                                                 // 4 flags
      "|\\b(\\d+(?:\\.\\d+)?)\\b" +                                             // 5 numbers
      (kw ? "|\\b(" + kw + ")\\b" : "|(\\x00)") +                                   // 6 keywords
      "|([{}\\[\\](),:;])",                                                           // 7 punctuation
      "g"
    );
    var CLASSES = [null, "s", "cm", "u", "fl", "n", "kw", "p"];
    var out = "", last = 0, m;
    while ((m = re.exec(code)) !== null) {
      out += esc(code.slice(last, m.index));
      var group = 0;
      for (var i = 1; i < CLASSES.length; i++) if (m[i] !== undefined) { group = i; break; }
      var cls = CLASSES[group];
      // a string followed by a colon is a key, not a value
      if (cls === "s" && /^\s*:/.test(code.slice(re.lastIndex))) cls = "k";
      out += cls ? '<span class="' + cls + '">' + esc(m[0]) + "</span>" : esc(m[0]);
      last = re.lastIndex;
    }
    return out + esc(code.slice(last));
  }

  function t(key, en) {
    var I = window.WelanceI18n;
    if (!I) return en;
    var v = I.t(key);
    return v === null || v === undefined ? en : v;
  }

  function paint(block) {
    block.querySelectorAll("pre[data-lang]").forEach(function (pre) {
      if (pre._raw === undefined) pre._raw = pre.textContent;
      // highlight() escapes everything it emits; the source is this page's own
      // static text, so no untrusted content ever reaches innerHTML
      pre.innerHTML = highlight(pre._raw, pre.getAttribute("data-lang"));
    });
  }

  function wire(block) {
    var tabs = block.querySelectorAll(".code-tabs button");
    tabs.forEach(function (b) {
      b.addEventListener("click", function () {
        var want = b.getAttribute("data-tab");
        tabs.forEach(function (x) {
          x.setAttribute("aria-pressed", x === b ? "true" : "false");
        });
        block.querySelectorAll("pre[data-tab]").forEach(function (pre) {
          pre.hidden = pre.getAttribute("data-tab") !== want;
        });
      });
    });

    var copy = block.querySelector(".code-copy");
    if (!copy) return;
    copy.addEventListener("click", function () {
      var pre = block.querySelector("pre[data-lang]:not([hidden])");
      var text = pre ? pre._raw || pre.textContent : "";
      var done = function () {
        copy.textContent = t("site.copied", "copied");
        copy.classList.add("done");
        setTimeout(function () {
          copy.textContent = t("site.copy", "copy");
          copy.classList.remove("done");
        }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () {});
      } else {
        var ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        try { document.execCommand("copy"); done(); } catch (e) {}
        document.body.removeChild(ta);
      }
    });
  }

  function label(block) {
    var copy = block.querySelector(".code-copy");
    if (copy && !copy.classList.contains("done")) copy.textContent = t("site.copy", "copy");
  }

  function boot() {
    document.querySelectorAll(".code").forEach(function (block) {
      paint(block);
      wire(block);
      label(block);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
  // the copy label follows the site language
  document.addEventListener("welance:lang", function () {
    document.querySelectorAll(".code").forEach(label);
  });
})();
