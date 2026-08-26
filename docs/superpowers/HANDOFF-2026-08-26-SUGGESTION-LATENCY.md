# Handoff — interactive suggestion latency and Gemini rollout

Date: 2026-08-26

This is the continuation document for the r001-15 session. The implementation
is present in this working tree but is **not committed or deployed**.

## Start here

The checkout is currently at a detached `HEAD`. Before committing, inspect the
release instructions and create/switch to the correct release branch without
discarding the working tree. Do not reset or re-checkout these changes.

Read, in order:

1. this document;
2. `docs/decisions/0002-default-model-selection.md`, addendum 2026-08-26;
3. `RELEASING.md`;
4. the working-tree diff.

## Problem that was reproduced

The Directory's `/api/directory/suggest` asks this service for three contextual
wizard answers. Against the deployed service:

- DeepSeek V4 Flash took **63.2 seconds**;
- `/v1/suggest` made one generation call and then one serial verifier call;
- the verifier accepted all three answers even though they were English for an
  `it-IT` request;
- `LOCALE_NAMES` contained `it`, not the browser locale `it-IT`, so the prompt
  silently lost its requested-language instruction;
- the deployed `PB_BYOK_MODELS` rejected all faster candidates with 422.

This is why p007 temporarily showed `AI NON DISPONIBILE` after changing its
preferred model: the remote r001-15 deployment had not yet acquired this
allowlist/model change. p007 now has a 422-only DeepSeek rollout fallback; once
this service deploys, its configured Gemini path will be used directly.

## Implemented changes

### `app/scorer.py`

- `/v1/suggest` defaults to one generation call. These are editable choices a
  human must select, not an authoritative verdict.
- `PB_SUGGEST_VERIFY=true` restores the previous second-model review.
- Unverified valid suggestions are cacheable for service-funded calls.
- Cache namespace moved from `pb:s2:one` to `pb:s3:one` and includes screening
  mode through the verifier component.
- Both suggestion endpoints resolve region-style locales through
  `locale_name()`.
- `/v1/suggest/all` remains screened and retains its retry loop.

### `app/settings.py`

- interactive default: `google/gemini-3.1-flash-lite`;
- `suggest_verify: bool = False`;
- `suggest_provider_sort: str = "latency"`;
- candidate BYOK allowlist added for the measured comparison;
- `locale_name()` resolves exact locales first (`pt-BR`) and then base language
  for browser variants (`it-IT` → `it`, `de-DE` → `de`).

### `app/llm_client.py`

- OpenRouter calls whose purpose begins with `suggest` include
  `provider: {sort: "latency"}`. Authoritative judging and verification do not
  silently inherit this routing policy.

### Deployment configuration

`.env.dev`, `.env.staging`, `.env.production` and `.env.example` now:

- include Gemini 3.1 in `PB_OPENROUTER_MODELS`;
- allow the benchmarked candidates through `PB_BYOK_MODELS`;
- set `PB_SUGGEST_MODEL=google/gemini-3.1-flash-lite`;
- set `PB_SUGGEST_VERIFY=false`;
- set `PB_SUGGEST_PROVIDER_SORT=latency`.

Published scoring remains DeepSeek V4 Pro. The DeepSeek Flash verifier remains
configured for `/v1/suggest/all` and for opt-in single-rule screening.

## Measurements

Single Italian camping-minimarket case, `success-metrics`:

| Model | Total | Result |
| --- | ---: | --- |
| Gemini 3.1 Flash-Lite | **0.96s** | 3 Italian choices |
| Gemini 3.5 Flash-Lite | 1.20s | 3 Italian choices |
| Claude Haiku 4.5 | 2.65s | 3 Italian choices |
| DeepSeek V4 Flash | 8.92s | 3 Italian choices |
| GPT-5 nano | 14.48s | truncated, no result |

Five-case multilingual sweep (Italian, German, English, French, Portuguese):

| Model | Mean | Schema/language | Human observation |
| --- | ---: | --- | --- |
| Gemini 3.1 Flash-Lite | 1.19s | 5/5 | best grounding balance |
| Gemini 3.5 Flash-Lite | 1.16s | 5/5 | invented more implementation constraints |
| Claude Haiku 4.5 | 2.78s | 5/5 | good, slower and over-specific |

The 30ms Gemini difference is not meaningful. Gemini 3.1 wins on grounding,
not a misleading claim of stopwatch superiority.

Benchmark runners live in p007-16:

- `scripts/benchmark-brief-suggestions.mjs`
- `scripts/benchmark-brief-suggestion-suite.mjs`

They read the configured key without printing it. Do not paste keys or private
briefs into logs or tickets.

## Verification already completed

```text
.venv/bin/python -m pytest -q
107 passed, 10 skipped

RUFF_CACHE_DIR=/tmp/pb-ruff-cache .venv/bin/ruff check \
  app/settings.py app/scorer.py app/llm_client.py \
  tests/test_verifier_loop.py tests/test_models_endpoint.py
All checks passed

git diff --check
passed
```

The pytest cache warning is sandbox-only: this session could not write
`.pytest_cache` in the sibling repository. It is not a test failure.

## Continuation checklist

1. Inspect `git status -sb`: preserve every listed working-tree change.
2. Review the diff and the policy distinction between interactive drafts and
   authoritative scoring.
3. Run the repository's full release checks from `RELEASING.md`; the focused
   Python suite above is already green.
4. Commit on the correct release branch and follow the repository's normal
   GitLab release/MR process. Do not tag manually if `RELEASING.md` says the
   pipeline owns tags.
5. Deploy develop/staging first.
6. Verify `/v1/models` includes `google/gemini-3.1-flash-lite`.
7. Send `/v1/suggest` with a caller key, model Gemini 3.1 and locale `it-IT`.
   Expect HTTP 200, three Italian suggestions, `X-PB-Verification-Ms: 0`, and
   normally low-single-second `X-PB-Generation-Ms`.
8. Verify `/v1/score` still reports DeepSeek V4 Pro and that `/v1/suggest/all`
   still reports its verifier.
9. Publish through the normal production path, then repeat steps 6–8 against
   `https://briefs.welance.com`.
10. Once production accepts Gemini, the p007 rollout fallback may remain as a
    harmless compatibility fence or be removed in a later cleanup.

## Do not accidentally change these boundaries

- Do not remove verification from authoritative scoring.
- Do not remove the screened retry loop from `/v1/suggest/all` as part of this
  latency change.
- Do not call three independent models to fake progressive answers. At about
  one second, returning one coherent three-choice set is faster and clearer.
- Do not log caller keys, briefs or raw provider bodies.
