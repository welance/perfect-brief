# Governance

This ruleset gates publication on welance/Directory. A bar with real
consequences has to be hard to game *and* hard to capture. We get there not by
controlling who may speak, but by separating three gestures that are usually
collapsed into one — and letting evidence, not authority, do the deciding.

## The three gestures

**1. Anyone proposes.**
Opening a pull request is fully open, GitHub-native, zero gatekeeping. A new
rule, a reweighting, a better source, a sharper criterion, a fixture that
exposes a blind spot — all of it arrives as a PR. The cost of contributing is
near zero by design. This is the gesture that makes "we are not the gatekeepers"
literally true: the door to propose is never locked.

**2. Evidence merges.**
A PR does not merge because a maintainer likes it. It merges because:

- it **passes the public fixture corpus in CI** (`python evaluate.py` stays
  green), and
- it gets **review**.

The corpus is a set of labelled example briefs with expected score bands. It
encodes the community's standing agreement about what good and bad briefs look
like. A change that quietly lowers the bar breaks the corpus, and CI rejects it.
To weaken the bar you would have to also weaken or delete fixtures — and that is
a visible, reviewable, suspicious diff. **The fixtures are the immune system.**
Review is the only human-judgment step, and its job is narrow: confirm the
change is sound, sourced, and honestly tested — not to express taste.

**3. Anyone forks.**
The whole ruleset is OSS. If you believe the bar is wrong and review won't move,
you can fork it and run your own. That exit right is the real anti-gatekeeper
guarantee: it disciplines maintainers better than any promise, because a bar
that drifts unfair loses its community to a fork. We keep the bar honest because
we *can't* keep it captive.

## Maintainership is earned, not appointed

Merge rights to the live bar (`/rules`, `/scoring.yaml`, `/fixtures`) sit with a
maintainers group. Nobody is appointed to it from above. You earn a seat through
a track record of good PRs — the ordinary OSS meritocracy. The group's job is
stewardship of the corpus and the review bar, not ownership of "good."

See `CODEOWNERS` for the current review surface and `CONTRIBUTING.md` for what a
mergeable PR contains.

## Why open, when Welance runs both sides

Welance operates the Directory *and* the bar that gates entry to it. That is a
genuine conflict of interest, and pretending otherwise would be the dishonest
move. Open-sourcing the bar is the structural answer: a metric you can read,
contest, test against public examples, and fork cannot be quietly rigged in the
operator's favour. The openness is not decoration — it is what makes the gate
*trustworthy* given that we have skin in the game.

## What is policy, and therefore contestable

Nothing about the bar is hardcoded conviction. All of it is diffable config,
reviewed like any rule:

- **Rule weights and severities** live in each rule file.
- **Thresholds** — the 75 (accept) and 40 (reserve) publication bands, the
  severity caps, the confidence threshold — live in `scoring.yaml`.

"We should care more about measurable outcomes" is a one-line weight change with
a rationale, not a mood buried in a prompt. If you think a threshold is wrong,
the disagreement has an address: a PR to `scoring.yaml`, decided against the
corpus.

## The one invariant

One thing is not up for a vote, because the whole audit story rests on it:

> The LLM returns a per-rule verdict (status + evidence + confidence) and
> **nothing else.** All weighting, capping, normalization, and the publish
> decision happen in code, deterministically, from inputs the model never sees.

Keep that wall and every score can be taken apart, reproduced, and argued with.
Breach it — let the model see weights, or tally its own score — and you trade an
auditable instrument for a vibe. PRs that blur this seam will be declined on
principle, however good the intention.

## The clock — how a proposal becomes the bar

The three gestures need one operational piece: time for the community to
actually show up. So every **rule-change PR** — anything touching
`perfect_brief/rules/`, `scoring.yaml`, or `fixtures/` — runs on a clock:

1. **The window.** The PR stays open at least **7 calendar days** from the
   moment it is complete (template filled, corpus green). Nothing merges
   inside the window, however good it looks — the window is not review
   latency, it is the community's standing invitation to disagree.
2. **The clock restarts** when the normative diff materially changes — a
   weight, a criterion, gate membership, a threshold. Editing prose or adding
   fixtures in response to review does not restart it.
3. **Objections must be actionable.** "This weakens the bar" names the
   fixture that proves it; "this source doesn't say that" quotes the clause.
   An actionable objection blocks merge until resolved in the thread.
   Unactionable taste doesn't stop the clock — that is what forking is for.
4. **Merge needs all four:** corpus green in CI · a maintainer review · the
   window elapsed · no unresolved actionable objection.
5. **Declines leave a trail.** A declined rule change is closed with the
   criterion it failed (evidence, corpus, invariant, scope) — and the door
   stays open: the same idea can return with new evidence, on a new clock.
6. **Fast lane.** Typos, link rot, and non-normative docs skip the window —
   nothing about the bar moves, so there is nothing to discuss.
7. **Every merge is a version.** Normative tweaks (weight, severity,
   criteria, a new rule) bump minor; removing a rule, changing gate
   membership, or moving a threshold bumps major; docs bump patch. The
   `ruleset_version` travels with every score, so any brief can name the
   exact bar it was judged against.
