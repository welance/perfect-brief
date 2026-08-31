# Theme

## Compact token summary

- Font: Maison Neue; system mono fallback for numbers and formulas.
- Paper/ink: `#fff`/`#0a0a0a`; dark `#0d0d0d`/`#f2f2f2`.
- Surfaces: `#f7f7f5`, `#efefec`; dark `#171717`, `#1f1f1f`.
- Brand: coral `#ff7b51`, yellow `#eecc5d`, violet `#8856cd`, cyan
  `#97dbe2`, blue-grey `#b8c5d6`.
- Spacing ladder: 4, 8, 12, 16, 20, 28, fluid 28–40, 40–56, 56–80px.
- Corners are square except intentional pills (`999px`).
- Max content width 1320px; horizontal padding `clamp(16px,4vw,56px)`.
- Borders are structural: light hairlines and 2px ink emphasis.
- Motion: 140–340ms; reduced motion removes transitions.

```css
:root {
  --paper:#fff; --paper-2:#f7f7f5; --paper-3:#efefec;
  --ink:#0a0a0a; --ink-soft:#4a4a4a; --rule:#e6e6e6;
  --wl-y:#eecc5d; --wl-c:#ff7b51; --wl-p:#8856cd;
  --wl-cy:#97dbe2; --wl-b:#b8c5d6;
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px;
  --sp-5:20px; --sp-6:28px; --sp-7:clamp(28px,3.2vw,40px);
  --sp-8:clamp(40px,5vw,56px); --sp-9:clamp(56px,7vw,80px);
}
:root[data-theme="dark"] {
  --paper:#0d0d0d; --paper-2:#171717; --paper-3:#1f1f1f;
  --ink:#f2f2f2; --ink-soft:#a2a2a2; --rule:#2a2a2a;
}
```
