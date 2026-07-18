# Welance restyle of the public pages — design

**Date:** 2026-07-18 · **Approved by:** Enrico (chat) · **Scope:** `site/*.html`, `app/static/index.html`, new `site/fonts/`, new `site/animations/`

## Goal

The public pages must read unmistakably as welance: same visual DNA as
welance.com and welance/Directory, with the GitHub repo and the Directory
relationship impossible to miss. The Lottie ident joins the house animation
family (`p007-16-welance-website/public/animations/`).

## Decisions (user-approved)

1. **Full Directory DNA** — Maison Neue self-hosted, black-on-white minimal,
   welance asterisk logo, Directory-style buttons.
2. **All pages** — `index.html`, `rules.html`, and both console copies
   (`site/console.html`, `app/static/index.html`, kept in sync).
3. **Real Lottie on the landing** — hand-authored
   `site/animations/the-perfect-brief.json`, played with lottie-web (CDN,
   deferred), current CSS stroke-draw SVG kept as no-JS / reduced-motion
   fallback. File stays copy-ready for the welance-website animations folder.

## Visual system

- **Fonts** (`site/fonts/`, copied from `r001-06-directory/fonts/`):
  MaisonNeue-{Book,Medium,Demi,Bold}.woff2 + MaisonNeueMono-Regular.woff.
  `@font-face` blocks identical to Directory `styles.css`. Google Fonts
  preconnect/link removed. *Note:* Maison Neue is a commercial license already
  served publicly by welance.com/Directory; the files now also live in this
  MIT repo — flagged to Enrico, accepted.
- **Tokens** (Directory values): `--bg:#fff`, `--fg:#0a0a0a`,
  `--muted:#4a4a4a`, `--muted-2:#6e6e6e`, `--line:#e6e6e6`,
  `--line-strong:#0a0a0a`, `--surface:#f7f7f5`, `--surface-2:#efefec`.
  Welance accents = the Lottie palette: yellow `#eecc5d`, coral `#ff7b51`,
  purple `#8856cd`, cyan `#96dbe3`.
- **Semantic colors** (pass/partial/fail/accent-blue) stay — functional, not
  brand — retuned to sit on white.
- **Buttons**: bordered `--fg`, transparent bg, invert on hover; `.primary`
  solid black. GitHub button = primary.
- **Type**: Maison Neue for display/body; Maison Neue Mono for kickers,
  labels, code.

## Branding & GitHub

- Header: welance asterisk+wordmark SVG copied verbatim from Directory
  `components/shared.jsx` (stroke-draw + glyph-stagger animation CSS from
  Directory `styles.css`), followed by `/ perfect brief` in brand-slash
  style. Logo links to welance.com. "built for welance/Directory" directly
  beneath.
- Hero CTA row keeps the octocat button with the full repo URL, restyled
  primary. Footer GitHub link stays.
- `rules.html` + consoles get the same slim branded header (static logo).

## Lottie: `site/animations/the-perfect-brief.json`

600×600, 30fps, ~180 frames, shape layers only, transparent bg. Narrative:
sheet draws in → brief lines type on → yellow highlight sweep → coral score
ring fills → purple check lands → small asterisk beat. Self-contained JSON
(no external assets), same palette as `directory-teams-ad.json`.
Embed: lottie-web from CDN with `defer`; if it loads, it replaces the
fallback SVG in `.pb-ident`; `prefers-reduced-motion` and no-JS keep the
static/CSS SVG.

## Constraints

- Surgical edits only (CLAUDE.md §6) — structure and copy untouched; this is
  a token/rule/asset swap plus a header block.
- Engine/tests untouched; `make test` must stay green.
- Tone rules apply to any text touched (none planned).

## Verification

Playwright screenshots of all three pages (fonts render, logo animates,
Lottie plays, fallback works with JS disabled); `make test`.
