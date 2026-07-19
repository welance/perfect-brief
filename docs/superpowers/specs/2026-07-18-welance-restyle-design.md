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

- **Fonts** — no copies (revised in-flight per Enrico, 2026-07-18). Loaded
  cross-origin from the canonical source `https://welance.com/fonts/*.woff2`
  (verified live: `access-control-allow-origin: *`, byte-identical to the
  Directory files). Preconnect + `font-display: swap`, system-ui fallback.
  Keeps the licensed binaries out of this MIT repo and gives one source of
  truth for every welance property.
- **Shared stylesheet** `site/welance.css` — the single home for tokens,
  `@font-face`, welance logo animation, and button styles; all three site
  pages link it (no duplicated inline token blocks). Exception:
  `app/static/index.html` keeps inline tokens — the API-served console must
  work offline with zero external requests. Follow-up idea (separate repo,
  not this change): publish canonical `welance.com/styles/welance-tokens.css`
  from `p007-16-welance-website` and link it everywhere.
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
