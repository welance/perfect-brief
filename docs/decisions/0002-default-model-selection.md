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

## Addendum — 2026-08-21

The role split is now explicit rather than inherited:

- authoritative publish scoring: `deepseek/deepseek-v4-pro`;
- suggestion generation: `deepseek/deepseek-v4-flash`;
- suggestion verification: `deepseek/deepseek-v4-flash`;
- Sonnet: not enabled on Welance deployments, including the caller-key path.

V4 Pro is invoked with `reasoning.effort: none` for scoring. On the same
develop brief this returned all fourteen verdicts in 15.97 seconds; the
provider-default reasoning path produced no HTTP response inside 90 seconds.
This is an extraction/rubric task, and deterministic code still owns scoring.

OpenRouter's public model metadata on this date lists V4 Pro at $1.60/M input
and $3.20/M output tokens, and V4 Flash at $0.08106/M input and $0.16212/M
output tokens. These values supersede the old estimate for operational planning
without rewriting the historical snapshot above. The service returns the
resolved model, enforces an operator allowlist, and keeps paid-provider spend
caps as the final cost boundary.

## Addendum — 2026-08-26

Interactive single-rule suggestions are now treated separately from both the
authoritative judge and the multi-gap repair loop:

- authoritative publish scoring: `deepseek/deepseek-v4-pro`, unchanged;
- interactive `/v1/suggest`: `google/gemini-3.1-flash-lite`, one generation
  call, OpenRouter latency routing;
- `/v1/suggest/all`: retains the screened retry loop and DeepSeek verifier;
- optional conservative single-rule screening: `PB_SUGGEST_VERIFY=true`.

Reason: the previous DeepSeek Flash path took 63.2s end to end because every
editable set waited for generation and a second LLM review. That review still
accepted three English answers requested with `it-IT`; regional locales were
not resolved by the exact-key locale map. After fixing locale resolution and
removing the redundant review, a production-shaped Italian comparison measured
Gemini 3.1 Flash-Lite at 0.96s, Gemini 3.5 Flash-Lite at 1.20s, Claude Haiku 4.5
at 2.65s and DeepSeek V4 Flash at 8.92s. GPT-5 nano truncated at the configured
800-token ceiling after 14.48s.

A follow-up five-case Italian/German/English/French/Portuguese sweep measured
mean totals of 1.19s (Gemini 3.1), 1.16s (Gemini 3.5) and 2.78s (Haiku). All
returned three parseable answers in the requested language. The 30ms Gemini
difference is noise; human review selected 3.1 because 3.5 more often invented
implementation constraints (offline operation, cloud storage, exact photo
counts). This selection applies only to editable suggestions. It does not
change the scoring model or deterministic aggregation boundary.
