# Shared UI primitives

The public UI is framework-free HTML/CSS/JavaScript. There is no component
directory or third-party component library. Shared primitives live in
`site/welance.css` and are instantiated directly by the pages.

```css
.effortbar { position: relative; display: flex; width: 100%; height: 46px;
  border: 1px solid var(--line-strong); background: var(--surface-2);
  touch-action: none; user-select: none; }
.grip { position: absolute; top: -5px; bottom: -5px; width: 26px;
  margin-inline-start: -13px; display: flex; align-items: center;
  justify-content: center; cursor: ew-resize; background: none; border: 0;
  padding: 0; touch-action: none; z-index: 2; }
.wl-app .wl-sheet { position: fixed; inset-inline: 0; bottom: 0; z-index: 101;
  display: flex; flex-direction: column; background: var(--paper);
  border-top: 2px solid var(--ink); padding-bottom: env(safe-area-inset-bottom); }
.wl-app .wl-dock { display: flex; align-items: baseline; gap: var(--sp-5);
  padding: 0 var(--sp-4) var(--sp-3); }
```

Page-local reusable vocabulary: `.card`, `.field`, `.role`, `.figures`,
`.fig`, `.formula`, `.verdict`, `.splitbar`, `.effortbar`, `.grip`.
