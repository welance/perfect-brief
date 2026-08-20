# The bar, examined — critique, inversion, repositioning

**Status:** working document, decided direction. Written 2026-08-12 from a full
adversarial audit of this repo, its public pages, and the welance/Directory
business-model docs (`r001-06-directory/docs/`). Written so that, with light
edits, it could itself be published — a project whose voice is "small claim,
true" should be able to show its own worst objections and what it did about
them.

**The one-line verdict:** the money is clean; the data posture and one gate
mechanism (M11) are not yet; every problem found is fixable, most with words,
four with work. The conflict of interest is not the project's shame — it is
the reason the bar must be open.

---

## 0. Decisions already taken

1. **Rename.** "Perfect Brief" → **The Brief Bar** (`brief-bar`). The copy
   already calls it "the bar" everywhere; the domain (`briefs.welance.com`)
   never said "perfect". The provocation lives in the gesture — publishing
   your own bar — not in the name. "perfect" survives only in the changelog.
2. **M11 restructure** (directory repo): a brief that passes the bar's gate is
   vetted — free, instant, automated. The paid Rebrief and the community vote
   remain as *remedies and optional help*, never as the only doors.
3. **The Operator Covenant**: a written, where-possible-testable set of
   commitments that binds *the house*, not the users (§4, PB-5).
4. **Honesty before growth**: the disclosure and covenant work ships before
   any commercial push. It is not ethics decoration; it is insurance on the
   only revenue engine (§6).
5. Fees stay symbolic; the Rebrief stays; the €5 direct-invite tier goes.

---

## 1. The 29 critiques and their inversions

Format: **critique → inversion → action** (action IDs resolve in §5).
An inversion counts only if it survives the person who wrote the attack.

### A. The number

- **A1 — No predictive validity.** Weights sum to 100, chosen by whom, on what
  evidence? No datum links "brief at 78" to any real outcome.
  → *Inversion:* the welance archive 2012–2026 (the Directory's own launch
  dataset, per R9) is the missing corpus. Re-score the original briefs,
  correlate with known outcomes (slippage, scope changes, margin). If the
  correlation holds: the only bar in the niche with receipts. If it doesn't:
  drop the score, keep the gate, **publish the negative study** — worth almost
  more. → **PB-10**
- **A2 — Consistency ≠ correctness.** Fixtures prove the system agrees with
  itself over time, not with a competent human. No inter-rater kappa anywhere.
  → *Inversion:* measure it. 3 reviewers × 50 archive briefs × 14 rules,
  per-rule Cohen's kappa, published. Low human-human agreement identifies the
  ambiguous rules to rewrite — the kappa becomes the ruleset's maintenance
  tool. Nobody in this niche publishes this number. → **PB-9**
- **A3 — False resolution.** A pass/partial/fail judge cannot support a 0–100
  continuum with decimals; 71 vs 74 is noise shown as signal.
  → *Inversion:* band first, number second ("indicative resolution"). Show
  exactly the precision you can defend. → **PB-12**
- **A4 — Goodhart, accelerated by openness.** Public bar + free judge +
  `/v1/suggest` = iterate until pass without improving the brief.
  → *Inversion:* for briefs, teaching to the test mostly *is* the skill —
  to pass `problem-defined` you must write the problem. Unlike SEO, the letter
  drags the substance with it. Must be tested, not hoped: adversarial fixtures
  in the corpus. → **PB-8**
- **A5 — Incomparability across ruleset versions.**
  → *Inversion:* briefs live 10 days (Directory M3); rulesets change slower.
  Live cross-version comparison ~never happens. Declare the constraint (no
  cross-version ranking) and the visible `ruleset_version` does the rest.

### B. The judge

- **B1 — Reproducibility expires with the model.** / **B2 — Temp 0 is not
  determinism** (MoE routing, batching, providers re-pointing slugs).
  → *Inversion:* the honest claim is **inspectability**, not replay: every
  verdict carries a verbatim quote a human can check forever, even after the
  model dies. Fix the wording; run the fixture corpus nightly against the live
  model as a **drift detector** — nobody else has one. → **PB-14**
- **B3 — Prompt injection in the judged text.** The gate — a publish
  decision — hangs on input that can attack the judge.
  → *Inversion:* the seam already caps the blast radius (injection can bend a
  verdict, never the math or the gate logic). Add injection briefs to the
  fixtures and publish them: "try to break the judge" is the most credible
  move an open project can make. → **PB-8**
- **B4 — i18n wider than validated.** 8 UI languages, judge quality per
  language unmeasured.
  → *Inversion:* extend the honesty already practiced — UI locales carry a
  draft badge until a native speaker reviews; judge languages get the same:
  measured per-language agreement, unvalidated languages badged. → **PB-13**
- **B5 — LLM where a regex suffices.** Floor, title, PII are deterministic
  problems.
  → *Inversion:* "deterministic where possible, model only where judgment is
  needed" — hybrid checks extend invariant #1 (the seam) into the rules
  themselves. The project becomes *more* itself. → **PB-7**

### C. The product

- **C1 — A feature, not a product.** Nobody wakes up wanting a grade on their
  brief; standalone demand ≈ 0.
  → *Inversion:* stop selling it as a product. It is **the Directory's
  vetting gate, made inspectable** — infrastructure with a window. The
  customer is the Directory; the public gets the right of inspection plus a
  free tool as a side effect. "Who buys it?" dissolves: it is not for sale.
- **C2 — Nobody asked.** No user research anywhere.
  → *Inversion:* the need is internal and documented — M11 (vetting gate),
  M2 (community votes), M5 (<3-pitches safety net) predate the code. Publish
  the origin story: "our noticeboard needed a bouncer." Also true and
  documented: the first scorer (2026-05-23) was an internal handoff-risk tool.
- **C3 — Sales will override the gate,** making it decorative.
  → *Inversion:* a blocked brief + `/v1/suggest` + the Rebrief path = the
  block is a redirect to improvement (free) or professional scoping (paid,
  R8). The gate *feeds* the flagship paid service instead of fighting sales.
  Aligned by construction — once M11 is fixed (DIR-1).
- **C4 — Free public API + server-side LLM = slow leak.**
  → *Inversion:* the cost structure is already right (mock free forever, LLM
  costs land on whoever benefits: the Directory for its briefs, BYOK for
  yours) — it needs to be *told* as a choice: no VC subsidy, no
  free-today-priced-tomorrow. → **PB-4**
- **C5 — Four integration routes, zero consumers.**
  → *Inversion:* one deliberate bet, not four scattered ones: briefs are
  written with assistants now, so `llms.txt` + MCP put the bar **inside the
  writing tool**. The consumer is the author's LLM. Reframe integrate.html
  around this single thesis; prune what doesn't serve it.
- **C6 — Opportunity cost.** Founder attention on infrastructure elegance.
  → *Inversion:* only by discipline: maintenance mode on plumbing; the
  effort moves to the validity study — the one output that directly serves
  sales (evidence = marketing). → **PB-13**, §6

### D. The OSS model

- **D1 — OSS without users is a liability** (obligations to nobody). /
  **D5 — Apache cosplay** (GOVERNANCE+CODEOWNERS+CoC for one maintainer).
  → *Inversion — the keystone of the D group:* **governance is for the
  governed, not the contributors.** The gate judges people — posters and
  teams. The 7-day window, public PRs, fixtures moving with rules exist for
  *those subject to the bar*. Due process exists for the judged, not the
  judges. One preamble sentence turns the apparatus from cosplay into the
  most serious thing in the repo. Zero contributors is irrelevant; the
  constituency exists from day one. → **PB-6**
- **D2 — MIT gives the crown jewels away.**
  → *Inversion:* the ruleset without the corpus, the study, and the
  noticeboard that enforces it is a list of opinions. A competitor adopting
  the bar spreads the method with welance's name in the commit history —
  that is what winning as a standard-setter looks like. The moat is the
  receipts, not the YAML.
- **D3 — Open governance over business policy** (the €10k floor is welance's
  price list; a community can't vote on it).
  → *Inversion:* the code already separates them (`context: directory`,
  deactivatable per request). Declare it: **two classes of rules** — quality
  rules (open to debate) and Directory policy (welance's, labeled, not up
  for vote). Ambiguity was the critique; the label is the cure. → **PB-6**
- **D4 — The fork paradox** (openness fragments "the one bar").
  → *Inversion:* a fork is a context, not a schism — the engine is built for
  alternative bars (swap `scoring.yaml`, same engine, rule-level comparable
  verdicts). "One bar" was never the claim; "a bar you can read and change"
  is. A fork validates the format.

### E. The posture

- **E1 — The vendor grades the paying client.**
  → *Inversion:* the algorithm is gentler than the social judgment it
  replaces. On the Directory a weak brief takes public −1 votes (M2) and rots
  unpitched. The gate intercepts **earlier, privately, with instructions to
  fix it** — free. The bouncer fixes your collar before you walk in, instead
  of letting the room boo.
- **E2 — "The Method" before an audience** (Basecamp shipped Shape Up *after*
  having one).
  → *Inversion:* Basecamp had an audience; welance has receipts — 14 years,
  ~100 real projects. Receipts beat followers as a license to publish a
  method. Requires actually publishing them (PB-10), and dropping the
  definite article: "our method, opened", not "the Method".
- **E3 — "Perfect" violates the house tone rule** (it *is* the hype word).
  → *Resolved:* rename (§0.1). → **PB-1**
- **E4 — 20/80 asserted with fake precision.**
  → *Inversion:* restate as a hypothesis born of ~100 projects, **which the
  validity study can test** (how much outcome variance does brief quality
  explain?). A hypothesis declared as one is a strength. → **PB-10**
- **E5 — A bar not lived** (do welance's own briefs pass it?).
  → *Inversion:* score the archive publicly: "our 2012–2019 briefs score a
  median of X; here is what we learned." The single most powerful honesty
  gesture available; turns the bar from imposed to inhabited. → **PB-10**
- **E6 — The arrogance is in the apparatus-to-evidence ratio** (modest words,
  institutional surface).
  → *Inversion:* fix from both ends — add evidence (PB-9, PB-10), prune
  apparatus (PB-13). Publishing this document is the capstone: an
  institutional-grade apparatus pointed at itself is the opposite of
  arrogance.

### F. Structural contradictions

- **F1 — Anonymisation fights quality** (context is what makes briefs good).
  → *Inversion:* the rule strips identity, not context (Directory M1: sector
  and content stay). A brief that needs the company name to be clear is
  under-specified. Writing a brief that stands without your name is a quality
  *test*, not a quality tax — the same reason science reviews double-blind.
- **F2 — The number you watch (mock) is not the number that gates you (LLM).**
  → *Inversion:* every developer already owns the mental model — **linter
  while you type, CI at the merge**. Label the two numbers exactly that way
  in the console and the treacherous seam becomes a familiar convention.
  → **PB-11**
- **F3 — BYOK trains the worst pattern** (paste your key into someone else's
  site), and the leak test protects the repo, not the deployment.
  → *Inversion:* three options ranked by trust required, all real:
  (1) self-host (`make up`, the key never leaves home — this is *why* it's
  OSS); (2) BYOK with spend caps and tested, published limits;
  (3) trust the server. Presented in that order, BYOK is the *declared*
  middle, not an anti-pattern. → **PB-4**

### G. The conflict of interest

- **G1 — Judge, gatekeeper, and contestant.** welance writes the bar, runs
  the noticeboard the bar gates, and pitches as a team on it.
  → *Inversion — the deepest one:* **the conflict is the reason the bar is
  open.** An operator who competes on its own board cannot afford a private
  bar. Public versioned rules (can't be moved silently), verdicts with quotes
  (inspectable), fixtures in CI (no silent renormalisation),
  `context: directory` labels on house policy. Openness is not idealism —
  it is the structural mitigation of the conflict. This one sentence gives
  the whole OSS apparatus its missing reason to exist. → **PB-2, PB-3, PB-5**
- **G2 — The gift is a funnel.**
  → *Inversion:* a funnel needs walls; every exit here is open (MIT,
  self-host, offline mock, no tracking, no signup, nothing retained). And
  the interest gets *declared*, not denied: "yes, we benefit if your brief
  improves and lands on our board — that is why it's free." Declared interest
  beats performed altruism, always. → **PB-3**
- **G3 — Year-1 data is ~100% welance-origin and welance pitches.**
  → *Inversion:* the disclosure the Directory's own docs already prescribe
  (05-clarity C3: "Saying it preempts"), extended to the judge: welance's
  briefs pass the same gate, same model, same version — and the
  `ruleset_version` on every verdict is the proof nobody got a different
  bar. The audit trail becomes the equal-treatment guarantee. → **PB-3, DIR-5**

---

## 2. What the deep audit found (2026-08-12, three parallel audits)

### 2.1 Clean, with evidence
- **Zero value-indexed revenue** anywhere in M5–M15: flat €10 fees, deposits
  always refund, no wallet, no expiring credits, no pay-to-rank, no paid
  visibility. R10 holds.
- **Coded self-restraints exist**: rebriefer barred from pitching
  (`pitch.teamId !== brief.rebriefBy`, binds welance too); the
  operator-favoring launch subsidy was *removed*; the residual `isOperator`
  flag is used to *exclude* welance (from half-price Rebrief picks).
- **The lineage is genuine**: internal handoff-risk scorer (2026-05-23,
  "onboarding intensity and warranty period, never to reject") → public
  rubric next day → this service. Not retrofitted marketing.
- **Honesty assets already on the pages**: the three-parties-see-your-key
  admission; "It scores articulation, not truth"; "Prose is not a guarantee.
  A failing build is."; GOVERNANCE.md's unhedged conflict paragraph.

### 2.2 Currently on the wrong side of the line
1. **Rules bind users; nothing binds the house.** The operator sees every
   brief pre-market (up to 30 days in `awaiting-vetting`), every reveal-call
   transcript ("not shared with either party by default"), a real-email +
   rate-card roster including people who never signed up, and the
   who-works-with-whom graph. No data-use clause, no non-solicitation, no
   "we never train on briefs", no retention limits — anywhere. The
   third-party mediator and 18-month structural review *existed and were
   removed* (changelog 2026-05-17).
2. **M11 sells the key to its own gate.** Verbatim: *"Gives R8 real demand …
   €295 is now the express lane to a pitchable brief, not a luxury."* The
   free door "could stall", paid nudge at day 14, death at day 30. The v1
   public rubric's base was explicitly conversion-tuned ("Do not raise base
   so high … or drop it so low the helper can't reach 85").
3. **The gravest silence: welance pitches, and no public page says so.**
   Zero occurrences across the site; the grammar even excludes welance from
   "teams". Meanwhile the good CoI paragraph sits collapsed behind a summary
   literally labeled "the fine print".
4. **data.html contradicts its own mechanism**: "never stored" vs a 24h
   verdict cache holding verbatim quotes keyed by `sha256(brief)`; "who you
   are: nowhere" vs IP-keyed rate-limit counters; "no analytics" vs a
   third-party CDN script.
5. **GOVERNANCE.md describes a bar that no longer exists** (75/40 bands,
   severity caps) — a free, verifiable hit against a project whose whole
   defense is auditability.

### 2.3 Over-engineering: the numbers
Core is lean — engine 2,035 lines, service 1,123, ~3.2k lines of Python
total including tests. The fat is severable and named: Method/Price/Team
≈ 4,760 lines (zero core deps), i18n ≈ 3,360 (36% of it price/team keys),
session plans ≈ 1,970, MCP 261 (keep — it *is* the C5 bet). Diagnosis:
not stupidly over-engineered — **mis-allocated**. Trust machinery (~1,100
lines) is justified by G1; it was built before its reason was written down.

---

## 3. The repositioning

> **The Brief Bar is the welance/Directory's vetting gate, made public.**
> An open, versioned ruleset that decides which briefs may enter a blind
> noticeboard — published so that the operator, who also competes on that
> noticeboard, provably cannot tune the metre in its own favour. Free to
> use, free to fork, deterministic where possible, model-judged only where
> judgment is needed. It scores articulation, not truth; the number is a
> hypothesis until the archive study says otherwise — and we publish that
> study either way.

Three sentences that must appear where the objections land:
1. "welance also pitches as a team on the Directory — same fees, same
   blindness, same gate, and the `ruleset_version` on every verdict proves
   nobody got a different bar."
2. "Yes, we benefit when your brief improves and lands on our noticeboard.
   That is why the tool is free, and why every exit — self-host, fork,
   offline mock — is open."
3. "The Operator Covenant binds us, not you: no lead-mining, no training,
   no sales contact from brief content — testable where code can test it,
   named plainly where it can't."

---

## 4. The five proofs (execution order)

| # | Proof | What it buys | Effort |
|---|-------|--------------|--------|
| 1 | **Words** (disclosure, covenant text, truth-fixes) | removes every screenshot in §2.2.3–5 | days |
| 2 | **Deterministic checks** (PB-7) + **adversarial fixtures** (PB-8) | injection defense + auditability of the gate | ~1 week |
| 3 | **Kappa study** (PB-9) | "the judge agrees with humans as much as humans agree with each other" — nobody in the niche has this | ~1 person-week |
| 4 | **Validity study on the archive** (PB-10) | the foundation: score ↔ outcomes. Decides whether the 0–100 score survives | weeks, highest value |
| 5 | **Published limits** (inspectability wording, drift detector, per-language badges) | the tone promise, kept | days |

---

## 5. Surface mapping — every change, both repos

### 5.1 This repo (perfect-brief-service → `brief-bar`)

| ID | Change | Files |
|----|--------|-------|
| **PB-1** | Rename to **The Brief Bar** / `brief-bar`: titles, H1s, README, repo name; domain unchanged; "perfect" survives only in CHANGELOG | `site/*.html`, `README.md`, repo settings |
| **PB-2** | Un-collapse the CoI paragraph (out of `<details class="fineprint">`); one-liner on data/security/integrate | `site/index.html:348`, `site/data.html`, `site/security.html`, `site/integrate.html` |
| **PB-3** | Add the missing sentence — "welance also pitches as a team…" — landing, rules, console (next to the publish CTA) | `site/index.html`, `site/rules.html`, `site/console.html` |
| **PB-4** | data.html truth fixes: "never stored" → "never stored beyond the 24h verdict cache (short verbatim quotes included; `no_cache: true` opts out)"; disclose IP counters + CDN request (or self-host lottie); add the four missing promises (no mining, no training, no sales contact from briefs, log retention period); three-options-by-trust framing for BYOK | `site/data.html`, `site/security.html`, `site/index.html:371` |
| **PB-5** | **OPERATOR-COVENANT.md** + covenant section on site. Testable where possible: extend the leak-canary pattern — a test asserting brief bodies never reach logs; name the untestable limit plainly (we run the DB), security.html-style | new file, `site/data.html`, `tests/` |
| **PB-6** | GOVERNANCE.md: fix stale 75/40 bands + severity caps (now 45/85 + gate); preamble "governance exists for the governed"; declare the two rule classes (quality = debatable; `context: directory` = welance policy, labeled, not up for vote) | `GOVERNANCE.md` |
| **PB-7** | Deterministic pre-checks for `budget-floor`, `clear-title`, `anonymised` (parse/regex/NER first, LLM fallback on ambiguity); fixtures move in the same commit | `perfect_brief/judge.py`, `rules/*.yaml`, `fixtures/` |
| **PB-8** | Adversarial fixtures: prompt-injection briefs, published as "try to break the judge" | `perfect_brief/fixtures/adversarial/` |
| **PB-9** | Kappa study: 3 reviewers × 50 archive briefs × 14 rules; per-rule kappa on rules.html; rewrite low-kappa rules | new `docs/validity/`, `site/rules.html` |
| **PB-10** | Validity study: score the 2012–2026 archive, correlate with outcomes; publish either result; 20/80 restated as the hypothesis under test; E5 self-scoring page | `docs/validity/`, `site/` |
| **PB-11** | Console: label mock = "draft check — like a linter" / LLM = "official verdict — like CI"; wire live mode through this server (already planned in README) | `site/console.html`, `site/code.js` |
| **PB-12** | Band-first display; number secondary with "indicative resolution" | `site/console.html` |
| **PB-13** | Split Method/Price/Team (+ `pricing.js`, `splitbar.js`, their tests, their i18n keys) to their own repo; freeze locales to en/it/de until per-language judge validation; archive `docs/superpowers/` plans | `site/`, `tests/`, new repo |
| **PB-14** | Wording: "reproducible" → "inspectable" (verdict quotes are the permanent audit trail); nightly fixture run against the live model as drift detector | `README.md`, `site/data.html`, CI |
| **PB-15** | **Fees-at-cost story + open cost ledger**: "the fees are priced to cover the rails" wording (always paired with the declared field interest), plus a published annual running-cost ledger (infra, judge calls, Stripe). Directory side: switch pitch deposits to uncaptured auth-holds so charge+refund Stripe fees stop bleeding | `site/index.html`, `site/data.html`, Directory `PRICING` docs |

### 5.2 Directory repo (`r001-06-directory`)

| ID | Change | Files |
|----|--------|-------|
| **DIR-1** | **M11 rewrite**: bar-gate pass = free, instant vetting door. Rebrief + community vote = remedies/optional help. Delete the "express lane" rationale sentence — from the doc and from the design | `docs/06-business-model-rules.md` (M11) |
| **DIR-2** | Purge stale prices (€148/€295/€60/€120 in M5/M6 vs retired canon); resolve the `isOperator` (M5) vs "no affiliation field" (M16) contradiction — keep the self-disadvantaging filter, document it as exactly that | `docs/06-business-model-rules.md` |
| **DIR-3** | Simplify: one handshake fee (€10) everywhere; drop the €5 direct-invite tier and the expire-then-price-doubles auto-conversion (M12) | `docs/06-business-model-rules.md` (M12), `PRICING` |
| **DIR-4** | Governance: operator data-use clause mirroring the Covenant; **call transcripts delivered to both parties by default** (creepiest asset → service feature); restore a third-party element (even lightweight: a named annual external reviewer) or state plainly why not | `docs/14-governance-and-affiliations.md` |
| **DIR-5** | The C3 disclosure their own doc prescribes: "welance pitches like any other team" on the manifesto and near the vetted-brief badge | site copy, manifesto |
| **DIR-6** | Archive brief-rubric v1 with the honest note: "superseded — its base was conversion-tuned; the service replaced it" | `docs/brief-rubric.md` |

---

## 6. The commercial model

### 6.1 The fact that decides everything
Platform take per fully-engaged transaction: **€30 max** (€20 handshake +
€10 rebrief fee). €10k/month from fees alone ⇒ ~450 opened engagements/month
⇒ 350+ briefs/month ⇒ €6M+/month of project value moved. Not a plan — a
fantasy at 5+ years. **At 5× prices it still doesn't close** (~90
engagements/month needed) and the only story ("0.2% to open, 0% on the
work") burns. Conclusion: **fee levels are irrelevant to revenue at any
honest or dishonest price.** Their job is filtering and proof, not income.

**The positive statement of the same fact:** the fees are priced to cover the
rails — an efficient, stateless infrastructure whose running costs (OVH
cluster, Redis, judge calls, Stripe processing) are small and publishable.
The goal of the platform layer is not income; it is a more open, more varied,
faster, *not money-hungry* ecosystem of projects looking for teams and teams
looking for projects. Two guardrails so this never becomes the next hostile
screenshot: (1) it always travels **paired** with the declared interest —
"the rails run at cost; welance earns on the field, not at the tollbooth" —
never alone, or it reads as a non-profit claim contradicted by the €10k/mo
engine; (2) it is made **verifiable**: publish the running-cost ledger
annually (→ PB-15). Detail to fix while we're at it: a charge+refund deposit
loses ~€0.40 of non-returnable Stripe fees per pitch — use uncaptured
authorization holds (as M12 already does) so the spam filter costs zero.

### 6.2 The engine: the two doors, declared
`method.html` already names them: *Directory — do it yourselves* /
*welance — we do it with you* (70/30 split at full autonomy). The honest
model: **the platform runs at ~zero margin; welance earns by winning work on
its own board, openly, at the same fees, behind the same blindness.**

| | ~Month 6 | ~Month 12–18 | Fees-only (contrast) |
|---|---|---|---|
| Briefs published /mo | 8 | 20 | 350+ |
| Platform fees | ~€220 | ~€550 | €10,000 |
| welance wins (30% split, avg €18k brief) | 1 → €5,400 | 2 → €10,800 | — |
| Rebriefs performed by welance (~€250) | 1 → €250 | 2 → €500 | — |
| **Total /mo** | **~€5,900** | **~€11,900 ✓** | unreachable |

**Target: €10k/month ⇐ two won briefs per month.** Everything else is noise.

### 6.3 The four commercial answers
1. **"Too honest?"** There is no such thing here: honesty is the only
   marketing budget. A 0.2%-take platform cannot outspend a 20%-take one; its
   only acquisition channel is being the thing people link when they're angry
   at Upwork. The real risk is honesty *without volume* — a distribution
   problem, not a positioning one.
2. **"Change prices?"** No (§6.1). One simplification: kill the €5 tier
   (DIR-3). The only price that matters is the Rebrief's, and it's already
   designed right (team-quoted, flat €10 platform fee).
3. **"Remove the Rebrief?"** Opposite. It is the only scalable, honest paid
   product in the system, with the golden rule already coded (rebriefer can't
   pitch → paid for honest thinking, not an audition). M11's sin was using
   the *gate* to manufacture its demand; with DIR-1 the demand becomes
   genuine. Removing the Rebrief to simplify = amputating the liver to lose
   weight.
4. **"Can it ever be a business?"** As a fee-fed platform: no, by
   construction. As a **dealflow machine for welance competing as an equal**:
   yes, and €10k/month is a sober target.

### 6.4 The single KPI and the funnel that isn't a trap
**KPI: quality briefs published per month** (demand side). ~~Nothing in either
repo currently addresses client acquisition — the gap to fill.~~ **Update
2026-08-13:** the gap is being filled in p007-16 — the `/directory/start`
quick-start (spec `docs/superpowers/specs/2026-08-12-directory-quick-start-design.md`:
three taps → assembled sentence → generated draft → `/v1/score` → send/PDF,
PostHog funnel with the decisive metric defined) plus the "Brief me"
ingest-first prototype (two doors: upload-what-you-have / start-from-nothing).
This *is* the acquisition machine; the watch-outs are logged below in §6.6. The bet
already built: briefs are written with assistants, so the bar lives inside
the assistant (`llms.txt` + MCP + free console) → better briefs → some land
on the board. Every exit stays open (self-host, fork, no signup), which is
what makes it a declared interest instead of a trap.

### 6.5 Order of operations — honesty is the insurance
If the revenue engine is "we win work on our own board", it has exactly one
catastrophic failure mode: the rigged-race scandal. Therefore the covenant,
the disclosures, and DIR-1 ship **before** the growth push. Transparency is
not the brake on the model; it is the insurance on it.

Fourth leg, optional, later: hosted bar for agencies/procurement (custom
ruleset + SLA, €200–500/mo). Demand unproven — **sell before building**:
three conversations; two yeses = it exists, otherwise it doesn't.

### 6.6 Quick-start / "Brief me" funnel — audit notes (2026-08-13)

Aligned with this document already (independently — good sign):
"stop advertising a pitch fee we do not charge" (a637b9e); spec §8 = the
Operator Covenant in embryo (nothing persisted, no brief body in logs/Sentry,
asserted in code); §6 "No threshold is defined in this repo" respects the
seam across repos; §4b earned shortcuts ("Done unlocks at 85 — you're at 72",
gate enforced in the handler); the prompt contract *implements the A4
inversion* ("the honest artefact and the high-scoring artefact are the same
artefact" — brackets required, inventing specifics forbidden); closed slot
schema kills most of the injection surface (B3); PostHog EU, no replay,
shape-never-content events.

Watch-outs to fix before ship:
1. **The prototype's privacy claim overshoots the architecture.** "Your
   document and your answers stay in this browser" is false the moment
   `/api/directory/draft` generates or a PDF/docx is extracted server-side.
   The spec's own wording is the right one — nothing *persisted*, stateless
   routes, nothing logged — the prototype copy must downgrade to it. Same
   lesson as data.html "never stored" (PB-4); don't re-create the
   vulnerability on the new surface.
2. **The budget slot hides the floor instead of declaring it.** Options
   €10–25k / €25–60k / >€60k — no path below €10k. That is choice
   architecture doing quietly what the bar does openly (the brief-rubric
   base-tuning pattern, in tap form). Add an "under €10k" option that routes
   honestly: "this board starts at €10k — here's why, and here's what you
   can do instead."
3. **The spec's open question — "confirm the real non-negotiable set against
   the ruleset" — has an answer, and it's a mismatch.** Spec picked sector /
   problem / outcome / budget; the actual gate is `clear-title` /
   `problem-defined` / `budget-floor` (not_fail) / `anonymised` (pass).
   Required-ness in the quick-start must derive from the gate, not be
   re-judged locally.
4. **"Whose brief is this?" (company name) must never enter the brief body
   or the Send payload** — only the PDF cover — or it trips the `anonymised`
   gate the flow is supposed to clear. Worth a test, not a convention.
5. **"N teams could match" counter**: with a year-1 roster ~100%
   welance-origin (G3), this number needs the disclosure nearby once real
   data is behind it, or it reads as manufactured abundance.
6. Drafting ownership: agree with the spec — stays in p007-16 while the
   request schema is closed slots; **moves to r001-15 as `/v1/draft` when
   the paste path lands**; the Operator Covenant must cover the draft
   endpoint either way (it sees brief-shaped content).

---

## 7. Roadmap

| When | What |
|------|------|
| Week 1 | PB-2, PB-3, PB-4, PB-6 (words); DIR-5 |
| Week 2–3 | PB-5 covenant + leak-test extension; PB-1 rename; DIR-1..4, DIR-6 (doc rewrites) |
| Month 1 | PB-7, PB-8 (code); PB-11, PB-12 (console); PB-13 split |
| Month 1–3 | PB-9 kappa; PB-10 validity study (the foundation) |
| After — and only after | The growth push: distribution of the free bar, the two-wins-a-month engine, public participation log |
