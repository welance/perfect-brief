# brief bar design system

The brief bar is a transparent, rules-first tool by welance. It should feel
precise, modest, inspectable, and quick. The interface is editorial utility,
not a dashboard and not a marketing app.

Use Maison Neue with system fallbacks. Use mono only for numbers, formulas,
small labels, and controls where alignment matters. Keep the white/near-black
paper-and-ink foundation in light and dark modes. Coral is the primary accent;
yellow, violet, cyan and blue-grey explain distinct parts of a calculation.
Never introduce gradients, glass, soft card stacks, decorative shadows, or
generic SaaS styling. Corners stay square except true pills.

Build spacing from the existing 4px ladder. Within a unit use 8/12/16/20px;
between major regions use 28/40/56px. Prefer fewer visible containers, clear
rules, aligned baselines, and a deliberate alternation of dense control areas
and open explanation areas.

Header: fixed on phones, compact and explicitly named `brief bar`; it should
preserve orientation without spending much vertical space. Desktop may remain
sticky but needs cleaner grouping and rhythm.

Calculator mobile UX: do not place the entire desktop result sidebar in a
bottom sheet. The persistent mobile surface must contain only the live answer
and the one most useful explanation/action. Detailed formula, reference tables,
and prose belong in the document or a deliberate details view. Prioritize
editing one decision at a time while the answer remains visible. Preserve the
real DOM, calculation engine, i18n, keyboard accessibility, RTL, reduced motion,
and desktop behavior.

Use only existing fonts, colors, spacing, square borders, and component styles.
