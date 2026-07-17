# ADR 0001 — A second model reviews the first (and why they currently share a lab)

Date: 2026-07-17 · Status: accepted

## Context

`/v1/suggest[/all]` generates brief-improvement suggestions with an LLM. A
suggestion can sound right — fluent, confident, on-topic — while being generic
filler or ungrounded in the actual brief. LLMs systematically overrate their
own outputs (self-preference bias; see the LLM-as-judge literature around
JudgeBench and RewardBench), so asking the generator to grade itself filters
little.

## Decision

Every generated suggestion is screened by a **separate verifier model** on
three deterministic-in-code criteria — *anchored* (engages this brief's actual
content), *on-rule* (satisfies the failing rule's requirement), *actionable*
(usable without guessing). Rejected suggestions are regenerated with the
reviewer's critique fed back, at most 2 retries; the last attempt ships with
its rejected review attached. The verifier LLM returns accept/reject verdicts
only; the loop, retry policy, and every decision live in `app/scorer.py`
(the project's seam invariant). Verifier failure never fails a request —
suggestions ship unscreened and flagged (`X-PB-Screened: false`).

The verifier model resolves via `PB_VERIFIER_MODEL`: an explicit slug, or
`auto` = the first allowlist model whose **vendor prefix differs from the
judge's** — cross-lab review by construction, because decorrelated training
lineages catch failure modes a model can't see in its own output. Cultural
decorrelation (an eastern-lab reviewer for a western-lab generator, or vice
versa) was evaluated and is one env line away.

## Current configuration — deliberately same-lab

As of 2026-07-16 the owner chose **cost-first**: judge/suggester
`deepseek/deepseek-v4-pro`, verifier `deepseek/deepseek-v4-flash` (explicit
`PB_VERIFIER_MODEL`, not `auto`). Different models and sizes, same lab: we
keep two-model review but trade away cross-lab decorrelation for ~15–20×
lower cost (see ADR 0002). Restoring cross-lab review is a one-line env
change (`PB_VERIFIER_MODEL=auto` plus a second-vendor slug in
`PB_OPENROUTER_MODELS`).

## Consequences

- Worst case 3 generations + 3 reviews per request (~$0.004 at current
  prices); accepted sets are cached, BYOK responses are not.
- The response stays `list[Suggestion]`; screening metadata is additive
  (per-item `review`/`verifier_model`, `X-PB-*` headers).
- Same-lab review is a weaker fluff filter than cross-lab; revisit per
  ADR 0002's policy.
