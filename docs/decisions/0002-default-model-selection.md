# ADR 0002 — Default model selection (judge, suggester, verifier)

Date: 2026-07-17 · Status: accepted · Snapshot date for all prices/benchmarks: 2026-07-16

## Context

The service needs a default judge/suggester and a default verifier on
OpenRouter (`PB_OPENROUTER_MODELS`, first slug = default). Selection criteria,
in order: (1) rubric-following quality for structured judging, (2) cost per
request at public-testing traffic, (3) availability through a single
spend-capped OpenRouter key, (4) decorrelation options for the verifier
(ADR 0001).

## Decision

`PB_OPENROUTER_MODELS=deepseek/deepseek-v4-pro,deepseek/deepseek-v4-flash` ·
`PB_VERIFIER_MODEL=deepseek/deepseek-v4-flash` — owner decision (2026-07-16),
cost-first.

## Snapshot (2026-07-16, OpenRouter live prices per 1M tokens)

| Model | In | Out | Role |
|---|---|---|---|
| deepseek/deepseek-v4-pro | $0.43 | $0.87 | judge + suggester (default) |
| deepseek/deepseek-v4-flash | $0.10 | $0.20 | verifier |
| anthropic/claude-sonnet-5 | $2.00 intro / $3.00 | $10.00 intro / $15.00 | evaluated: best rubric-following tier |
| z-ai/glm-5.2 | $0.96 | $3.01 | evaluated: open-weight leader, eastern-lab verifier candidate |
| openai/gpt-5.6-terra | $2.50 | $15.00 | evaluated: third-lab alternate |

Measured on the real prompts (judge ≈1.1k tokens in / ≈1.2k out): a full
14-rule score ≈ **$0.0015**; a screened suggestion pass ≈ $0.0014; worst-case
loop (3 gen + 3 review) ≈ $0.0042. Simulated month at 70/25/5
casual/engaged/heavy mix: 100 testers ≈ $0.75, 1k ≈ $7.50, 10k ≈ $75. The
premium lineup (Sonnet 5 + GLM-5.2) measured ~15–20× higher. Hard spend
ceiling = the OpenRouter key's cap; redis rate limiting and the suggestion
cache bound abuse; BYOK bills the caller.

## Revisit policy

Re-evaluate this ADR when any of: (a) Claude Sonnet 5 intro pricing ends
(2026-08-31); (b) a ruleset major version bumps; (c) the live-judge false
positive/negative rate observed on real briefs argues for the premium tier;
(d) cross-lab verification (ADR 0001) is re-enabled. Record each re-evaluation
as a dated addendum here rather than editing the snapshot above.
