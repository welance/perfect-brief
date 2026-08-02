# PLAN — Perfect Price

> **Superseded 2026-08-01** by
> `docs/superpowers/plans/2026-07-31-perfect-method-price-team.md`
> (spec: `docs/superpowers/specs/2026-07-31-perfect-method-price-team-design.md`),
> which executed Phases 0–2 of this plan and extended them: shared engine in
> `site/pricing.js`, `team.html`, `method.html`, site-wide i18n (8 languages),
> multilingual judge guarantee. Phases 3–4 below (the €50/h cap decision, CoL
> real sources, native-speaker reviews — now one per language, the five open
> decisions, the permalink idea) are **still owed** and queue after it.

**Goal.** Publish **Perfect Price** as the second public surface of this project,
beside *The Perfect Brief*: a page explaining how Welance prices collaborations,
with a calculator anyone can use and check.

Perfect Brief is about being clear on **what the work is**.
Perfect Price is about being clear on **what it is worth, and who gets what part**.

Framing, in Enrico's words: sustainable *in human terms* — not maximising
profit, but maximising transparency and clarity between people. **People over
Budgets**, giving full expression to *Capitale Umano*.

This plan is independent of `PLAN.md` (publish + deploy the scoring service).
Do that one first if both are open; nothing here blocks it.

## What already landed

| Path | What it is | State |
|---|---|---|
| `docs/perfect-price/PERFECT-PRICE.md` | The whole concept: the rule, the reasoning behind every choice, what was rejected and why, five open decisions, implementation notes | Complete, written to be published |
| `site/price.html` | The calculator. Self-contained, no build step, no external requests | Works, **not yet styled to `welance.css`** |

Both are **fully anonymised** — no names, no individual compensation. That is
deliberate and must stay true: `site/` is public.

## The model in one box

```
margin = (client_rate − payout) / client_rate  ≥  m(level)

AUTONOMOUS    m=30%   share 70%   coverage 100%
WITH REVIEW   m=40%   share 60%   coverage  75%
WITH SUPPORT  m=50%   share 50%   coverage  50%

share = 30% + 0.4 × coverage        (the three levels are one line, sampled)
```

Coverage comes from decomposing a role into 2–5 **parts**, each scored
full/partial/none by the independent *and* by the most role-adjacent senior
member. Read `PERFECT-PRICE.md` before changing any of it — every constant has a
reason recorded there.

---

## Phase 0 — Read (no changes)

1. `docs/perfect-price/PERFECT-PRICE.md`, all of it. Especially §10 (open
   decisions) and §12 (what was rejected and why) — the second exists so
   settled questions do not get reopened.
2. Open `site/price.html` in a browser. Switch work type, change coverage,
   toggle the cost-of-living coefficient, press reset.
3. `site/index.html` — the voice reference. Modest, sincere, no hype.

**Acceptance:** you can state what the three levels mean without looking.

## Phase 1 — Make it look like the rest of the site

`site/price.html` currently carries its own complete stylesheet. The site has
`welance.css` and an established look (`index.html`, `console.html`,
`rules.html`).

1. Port `price.html` onto `welance.css`, keeping its own component styles only
   where the shared sheet has no equivalent (the split bar, the coverage
   ladder, the parts grid).
2. Keep every behaviour: five languages incl. Urdu RTL, per-mode default part
   sets, dirty tracking in `localStorage`, reset, both themes.
3. Add breadcrumbs matching the other pages (`welance / perfect price / …`).
4. **Surgical edits only** to `index.html` — add `price.html` to the nav and
   footer links. Do not rewrite the page.

**Acceptance:** `price.html` sits beside `console.html` without looking foreign;
nothing in the calculator regressed.

## Phase 2 — The explanatory page

`PERFECT-PRICE.md` is the source. `rules.html` is the precedent for turning long
reasoning into a page.

Lead with the problem, not the formula: a rule nobody can compute is a rule
nobody can check. Then the levels, then the calculator, then the open decisions
— publishing those unresolved is the honest move, and it invites the argument
rather than hiding it.

**Acceptance:** a reader who has never heard of Welance can compute their own
split and say where they disagree.

## Phase 3 — Decide what is public

Two things need a decision before this goes live.

1. **The internal-work mode reveals the internal rate cap (€50/h).** Fine to
   publish if that is a deliberate act of transparency — it is arguably the
   most transparent thing on the page. Not fine by accident. Decide, then act.
2. **The cost-of-living coefficients are estimates, not sourced figures.**
   Either replace them (OECD PPP, World Bank ICP, Numbeo) or label them clearly
   as illustrative. Publishing unsourced numbers that could set someone's pay is
   the one thing here that could do real harm.

**Acceptance:** a one-paragraph note in this file recording both decisions.

## Phase 4 — Before anyone is paid from it

- **Native-speaker review of the Urdu.** The strings are machine-written. The
  other four languages are solid but a check costs little. Reviewing them with
  an Urdu-speaking member is also a good way to introduce the model.
- **Resolve the five open decisions** (§10) with the collective. Several are
  currently just defaults sitting in code, which means the code is quietly
  making policy.
- Consider a shareable permalink: encode state in the URL hash so an assessment
  can be sent to the other party instead of re-entered.

---

## Provenance

Designed 2026-07-31 in the private `welance-admin` cockpit, from real
engagement data, then moved here because pricing policy is not cockpit scope.
The identified analysis — who earns what, unbilled hours, unreconciled invoices
— stays in that private repo and **must not be brought into this one**.

The model reproduces two existing engagements exactly, without changing anyone's
pay. It did not set prices; it explained the ones already being paid.
