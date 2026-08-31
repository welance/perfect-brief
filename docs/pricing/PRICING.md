# Price Split

**How welance prices collaborations, and why it works this way.**

A companion to *Brief Bar*. Where Brief Bar is about being clear on what
the work is, Price Split is about being clear on what the work is worth and
who gets what part of it.

> **People over Budgets.** A collective is only as honest as its arithmetic. This
> document exists so that anyone — a freelancer joining for one engagement, a
> studio taking on a role, a client wondering where their money goes — can
> compute the split themselves and check it. Nothing here is designed to
> maximise profit. It is designed to maximise clarity, so that the relationship
> between people is not mediated by a number nobody can explain.

**Status:** design agreed, five decisions deliberately open (§9).
**Audience:** members of the collective, prospective collaborators, and whoever
picks this up next to build it.
**Privacy:** all examples are anonymised. This document contains no individual
compensation data by design — it is meant to be published.

---

## 1. The problem this solves

welance charges a fee on top of the work it brokers and delivers. The stated
rule was: **minimum 30%, higher when the person filling a role is not fully
self-sufficient in it.**

That rule was never written down as anything computable. In practice the share
reaching the independent varied from roughly 50% to roughly 70% of the client
rate, with no visible logic connecting the two ends. Two people doing comparable
work could receive very different fractions of what the client paid, and neither
could tell you why.

**In a collective whose first principle is fairness, a rule nobody can compute is
a rule nobody can check.** That is the whole motivation. Not a pricing
optimisation — a legibility fix.

There is a second motivation, quieter but just as real. When the fee is opaque,
every negotiation becomes a test of confidence and bargaining appetite rather
than a shared reading of the facts. People who ask get more; people who do not
ask get less. That is not a neutral outcome — it systematically disadvantages
the people least comfortable advocating for themselves, which in practice tends
to mean the newest, the youngest, and those furthest from the centre of the
network. A computable rule removes that gradient.

---

## 2. Vocabulary

| Term | Meaning |
|---|---|
| **Independent** | The counterparty delivering a role. May be one freelancer or a studio of up to ~25 people. **The model does not distinguish.** |
| **Role** | What the engagement needs covered, e.g. *FullstackDev & Web Projects Maintainer*. |
| **Part** | One component of a role — the CMS, the client relationship, the infrastructure. A role has 2–5 parts, agreed at staffing. |
| **Coverage** | How much of the role the independent covers unaided, 0–100%. |
| **Level** | The delivery arrangement that coverage implies. Three values. |
| **Client rate** | What the client pays per hour. A negotiated fact — it never moves in this model. |
| **Payout** | What the independent receives per hour. This is the output. |

### A note on language that matters more than it looks

The three levels describe **how the role is delivered, never who delivers it.**

An early draft called the lowest level *"in crescita"* — "growing". That was
rejected, correctly. It describes a person as incomplete. The replacement,
**WITH SUPPORT**, describes an engagement: *this role is delivered with support
on the infrastructure.* That sentence is a fact about the work, observable by
anyone, and usually the independent is the first to say it out loud.

The distinction is not cosmetic. A model that labels people invites defensiveness
and hides information — nobody volunteers that they need help if needing help
lowers their standing. A model that labels arrangements invites accuracy. In
practice the person doing the work is the best source of truth about which parts
they cover, and the naming determines whether they tell you.

---

## 3. The rule

One inequality. Solve it in whichever direction the negotiation fixes first.

```
margin = (client_rate − payout) / client_rate   ≥   m(level)

client_rate known  →   payout      ≤ client_rate × (1 − m)
payout known       →   client_rate ≥ payout / (1 − m)
```

| Level | Margin `m` | Share to independent | Coverage |
|---|---|---|---|
| **AUTONOMOUS** | 30% | 70% | 100% |
| **WITH REVIEW** | 40% | 60% | 75% |
| **WITH SUPPORT** | 50% | 50% | 50% |

Equivalently, and this is where the levels come from:

```
share = 30% + 0.4 × coverage
```

evaluated at 100 / 75 / 50% coverage. The three levels are not arbitrary
buckets — they are one straight line, sampled three times. Discrete levels were
chosen over the continuous form because *"are you at 72 or 78?"* is an
unanswerable question that invites arbitrary precision, while *"do you handle the
infrastructure alone?"* has an answer.

### What "30%" means, precisely

The original wording — *"30% on top"* — is ambiguous, and the ambiguity is worth
about seven points.

- Read as a **markup on cost**: `client = payout × 1.30` → on a €85 rate the
  independent gets €65.38, a **23% margin on revenue**.
- Read as a **margin on revenue**: `payout = client × 0.70` → on a €85 rate the
  independent gets €59.50, a **30% margin**.

**This model fixes the canonical meaning as margin on revenue.** It is the more
generous of the two readings and the one already used in practice on live
engagements. Any future edit that quietly switches back to the markup reading is
a pay cut wearing the same words.

### The extra margin is a risk premium, not a support budget

Where coverage is partial, the retained margin prices the risk the collective
carries: rework, delay, a client relationship that needs a second pair of hands.
It is **not** an internal recharge for whoever helps out — that person bills
their own hours normally, like anyone else.

This distinction matters for a reason that is easy to miss. If the extra margin
were a support budget, the collective would have an incentive to find support
work to justify it. As a risk premium, the incentive runs the right way: reduce
the risk, and the premium goes away.

---

## 4. Deriving the level: decompose the role

This is the part that makes the model humane rather than merely arithmetic.

```
coverage = Σ(weight_i × agreed_i) / Σ(weight_i)          agreed_i ∈ {0, 0.5, 1}

AUTONOMOUS    if coverage ≥ 87.5%
WITH REVIEW   if coverage ≥ 62.5%
WITH SUPPORT  otherwise                    (floor — never below a 50% share)
```

For each part, two views are recorded: the independent's own, and the reviewer's.

```
agreed = mean(self, reviewer), rounded TOWARD the independent
         when they differ by one step        (0.75 → 1.0 ;  0.25 → 0.5)

|self − reviewer| = 2 steps   →   do NOT average. Discuss.
```

### Why decomposition changes the nature of the conversation

Scoring parts instead of people converts an act of judgement into an observation.

Nobody has to rule on whether someone "is autonomous". Someone records that the
infrastructure is verified by a colleague. That is checkable, it is not a verdict
on anyone's worth, and — crucially — it is usually something the independent
raises first, because raising it is the professional thing to do.

A model that penalised asking for help would be a model that punishes the exact
behaviour that keeps projects healthy. This one does the opposite: asking for
help is what makes the coverage assessment accurate, and accuracy is what makes
the price fair.

### The level becomes a map, with a price on it

Because coverage is per-part, every uncovered part has a number attached.

> *Covering the infrastructure takes this engagement from €50/h to €70/h.*

That is not a performance review. It is an offer, with an amount, that the
independent controls entirely. The calculator computes it per part automatically.

Three properties follow, and they are the reason this design was chosen over a
holistic seniority rating:

1. **It is falsifiable.** Either you handle the pipeline alone or you don't.
2. **It is actionable.** The path from one level to the next is a list, not a vibe.
3. **It expires.** Coverage is reassessed; a level is never a permanent label.

### The level belongs to the pair, not the person

**A level attaches to a person-and-role pair.** The same independent can be
AUTONOMOUS on one role and WITH SUPPORT on another, simultaneously, without
contradiction. Reviewed at every renewal, and re-openable at the independent's
request at any time.

---

## 5. Who reviews, and why that is not a hierarchy

The reviewer is the member whose **active role is closest** to the role being
assessed, and whose **seniority is higher** — where seniority means the
combination of hours and tenure in the collective, technical capability, and
internal administrative responsibility.

A CTO-like member assesses an incoming engineer. Not because they outrank them —
because they do the same craft and have done more of it.

**Authority here comes from role proximity, not ownership.** This is what keeps
the assessment compatible with a flat structure. The person reviewing is not
above; they are alongside, and further along. Custodians and owners have no
special standing in this process unless they happen to be the closest role.

Two of the three seniority inputs — hours/tenure and internal administrative
role — are computable from time-tracking data. Technical capability is not, and
should not be. So a tool can **propose who should review**. It must never
propose how much.

### Disagreement is a signal, not a problem to average away

A one-step gap rounds toward the independent: the residual uncertainty pays the
person, not the company. That is a deliberate asymmetry, and it is the cheapest
possible way to make the model visibly generous at the margin.

A two-step gap — one says *full*, the other says *none* — is **not averaged**.
It means the two parties disagree about what the engagement actually is, and
that disagreement is far more valuable than the number that would come out of
splitting it. The calculator refuses to compute and flags the row.

---

## 6. Internal work

Internal work has no client, so there is no rate to take a share of. Nothing to
apply a percentage to. It needs its own basis:

```
payout ≤ INTERNAL_CAP × ( share(level) / 0.70 )        INTERNAL_CAP = €50/h
```

| Level | Internal ceiling |
|---|---|
| AUTONOMOUS | €50.00/h |
| WITH REVIEW | €42.86/h |
| WITH SUPPORT | €35.71/h |

Administrators bill their administrative and account-management time this way,
funded out of the fee.

### The thing to watch, stated plainly

Internal time is the quiet way a margin disappears.

On a modelled engagement, administrative time at half a day per week consumes
roughly **19%** of the contract's gross margin. At one day per week it consumes
almost the **entire year's gain**. The break-even is under three days a week.

The cap keeps internal time cheap relative to delivery, but it does not make it
free. And untracked internal time is worse than expensive time, because it looks
like zero.

**There is a fairness dimension here that is easy to miss.** In a collective, the
people most likely to absorb unpaid internal work are the ones who feel most
responsible for the whole — typically founders and long-tenured members. That
looks like virtue and reads like dedication. It is also, structurally, the same
thing as unpaid labour, and it makes the company's real cost of operating
invisible to everyone including the people doing it. A collective that would
call 500 unpaid hours exploitation when a freelancer does them should call it
that when a custodian does them.

**Track internal hours to a code. From day one.** Not for control — because the
number decides whether the year closes up or down, and without it nobody knows.

---

## 7. Cost of living

```
payout_local = payout_role × max(coefficient, floor)
```

**This is the only rule in the model that does not follow from role coverage,
and it should be treated with corresponding suspicion.**

An AUTONOMOUS independent covers the whole role regardless of where they live.
The reduction comes purely from geography. It is defensible as a stated policy
and indefensible as a silent default.

Therefore the calculator **always displays what the role alone would pay**, and
shows the difference as its own separate band, in its own colour, on the split
bar. The differential is never allowed to quietly disappear into margin.

Three questions have to be answered explicitly by any collective that adopts it:

1. **Where does the differential go?** If it silently becomes margin, the
   collective profits from where somebody lives. Naming a destination — reserve,
   solidarity fund, reinvestment — makes it arguable rather than assumed. This
   is the single most important of the three.
2. **What is the floor?** Without one, a strict purchasing-power index can cut a
   fully-covering independent's pay by 70%+. A floor is what distinguishes a
   cost-of-living adjustment from arbitrage.
3. **Where do the coefficients come from?** The ones shipped in the calculator
   are estimates and nothing more. Replace them from OECD PPP, World Bank ICP,
   or Numbeo before anyone is paid from them.

A useful calibration: a collective already paying roughly double what a strict
index would give is not applying an index — it is applying a judgement, and
should say so.

---

## 8. The no-deal rule

> **If the independent's rate exceeds what the level allows, and the client will
> not pay `payout / (1 − m)`, the engagement does not happen.**

Nobody is compressed below their own rate to make a margin work.

This is the clause that keeps the model generous under commercial pressure, and
it is the one most likely to be quietly eroded when a quarter looks thin. It
should survive every future edit. A pricing model without a walk-away point is
not a pricing model; it is a ratchet.

---

## 9. Worked examples (anonymised)

| Engagement | Client rate | Coverage | Level | Payout |
|---|---|---|---|---|
| Full-stack engineers on a support retainer | €85/h | 100% | AUTONOMOUS | €59.50/h |
| Maintainer on a web project | €100/h | 50% | WITH SUPPORT | €50.00/h |
| Internal knowledge-base maintenance | — | 100% | AUTONOMOUS | €50.00/h |

The second decomposes as:

| Part | Coverage |
|---|---|
| CMS | full — 1.0 |
| Client relationship | partial, needs verification — 0.5 |
| Infrastructure & pipelines | none, needs support — 0.0 |
| **Role coverage** | **50%** |

**Both engagements were priced by instinct before this model existed, and the
model reproduces both exactly.** That is the strongest available evidence that
the shape is right — the rule did not change anyone's pay, it explained it.

One correction worth recording, because it is instructive. An earlier reading of
these two engagements flagged the 70%-vs-50% difference as a fairness breach. It
was not. It assumed the maintainer was fully self-sufficient in that role, and
they were not. **The apparent inequity was the absence of a written rule, not the
presence of an unfair one.** Most suspected unfairness in a collective is
probably this: not malice, just arithmetic nobody wrote down.

---

## 10. Decisions deliberately left open

These change what people are paid. They belong to the collective, not to whoever
writes the model.

1. **Part weights.** All weights are 1 by default. Should the client
   relationship count for more than a pipeline?
2. **Target or minimum?** Is `m` the margin actually taken — share follows the
   level, surplus on well-paid clients stays with the company — or a floor above
   which surplus is shared with the independent? The worked examples hold either
   way. Future engagements will not.
3. **Where the geographic differential goes.** (§7)
4. **The coefficient floor.** (§7)
5. **A real source for the coefficients.** (§7)

---

## 11. The calculator

`calculator.html` — single file, no build step, no external requests. Open it in
a browser.

**What it does**

- Role decomposed into parts; per part, two assessments (self and reviewer)
- Coverage → level → share, computed live
- Split bar showing client rate divided between independent, geographic
  differential, and company
- **"How to move up"**: every uncovered part priced in €/h
- Client-work and internal-work modes, with separate default part-sets
- Cost-of-living coefficient with a country list, an editable coefficient and a
  floor
- No-deal check against the independent's asking rate, collapsed by default

**Implementation notes for whoever picks this up**

- Five languages: English (default), German, Italian, Urdu, Brazilian
  Portuguese. Urdu switches the document to RTL. Numbers format via `Intl` with
  the matching locale.
- **The Urdu strings are machine-written and need a native-speaker review.** Do
  this before publishing. Reviewing them is also a good way to introduce the
  model to an Urdu-speaking member.
- Fonts are system stacks by design — a strict CSP blocks font CDNs, and a
  linked webfont would fail silently to a fallback.
- Themes: tokens on `:root`, redefined under `prefers-color-scheme: dark` and
  again under `[data-theme]` so a viewer toggle wins in both directions.
- State: per-mode default part-sets, per-mode dirty flags, persistence in
  `localStorage` under `welance-share-calc-v1`, and a reset that clears it. A
  default set follows the UI language; a user-edited set never gets overwritten.
- The client rate is an input and never an output. Only the payout moves when
  coverage or the coefficient changes. This was a deliberate correction: a
  negotiated number must not shift when someone adjusts a dropdown.

**Suggested next steps**

1. Native-speaker review of the Urdu (and ideally the other translations).
2. Replace the cost-of-living coefficients with sourced figures.
3. Resolve the five open decisions with the collective; several are currently
   just defaults in code.
4. Consider a shareable permalink — encode the state in the URL hash so an
   assessment can be sent to the other party rather than re-entered.
5. If this goes on a public site, decide whether the internal-work mode belongs
   there or in an internal-only build.

---

## 12. If you are another session picking this up

**What is settled:** the constraint and its two solved forms; the three levels
and their derivation from `share = 30% + 0.4 × coverage`; role decomposition into
parts with two-view scoring and rounding toward the independent; the two-step
disagreement stop; reviewer selection by role proximity plus seniority; the
internal-work cap at €50/h scaled by level; the no-deal rule; the canonical
meaning of "30%" as margin on revenue.

**What is not settled:** the five decisions in §10.

**What was rejected, and why** — so it does not get reinvented:

- A continuous 0–100 self-sufficiency score. False precision; "why 72 and not
  78?" has no defensible answer.
- Naming the lowest level after the person's development stage. Demeaning, and
  it suppresses the disclosure the model depends on.
- Disqualifying an invoice by supplier name alone when reconciling. An
  accountant both bills you for real work *and* appears as issuer on your own
  invoices; only name **plus** amount-match is safe.
- Treating the fee as covering support hours. It is a risk premium; treating it
  as a support budget creates an incentive to manufacture support.

**The tone to keep.** This document is deliberately not neutral. It states where
the model is generous, where it is contestable, and where it could be abused.
A pricing document that reads as purely technical is one that has hidden its
value judgements rather than removed them.
