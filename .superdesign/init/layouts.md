# Shared layouts

## Site chrome

- Source: `site/chrome.js`
- Mounts into `#site-header` and `#site-footer` on all nine pages.
- Header renders the asterisk + `brief bar_`, release status, calculator and
  integration links, language/source/directory actions, and the phone menu.
- Footer renders the full welance provenance lockup and grouped navigation.

```js
function lockupHead() {
  return '<a class="wl-brandline" href="./" aria-label="brief bar">' +
    MARK + '<span class="wl-project"><span class="name">' +
    tt("chrome.slash", "brief bar") + '<span class="b">_</span></span></span></a>';
}
function renderHeader() {
  var host = document.getElementById("site-header");
  if (!host) return;
  host.innerHTML = '<div class="wl-head"><div class="wl-head-in">' +
    lockupHead() + '<span class="wl-status" id="wl-release">© 2011–2026 · live</span>' +
    '<nav class="wl-nav" aria-label="Main">' + nav + '</nav>' +
    '<div class="wl-head-right">…</div></div>' + rule() + '</div>';
}
```

## Calculator layout

Both calculator pages use `.wrap > header` followed by `.cols`: editable
inputs on the left and `.sticky` computed output on the right. At 920px the
grid becomes one column. The current phone layer turns `.sticky` into a fixed
bottom sheet and mirrors two result figures in its grab area.
