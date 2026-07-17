# Suggestion verifier loop (verifier-of-the-verifier) — design

Date: 2026-07-16 · Status: implemented 2026-07-17 (plan: docs/superpowers/plans/2026-07-17-suggestion-verifier-loop.md) · Spec author: Claude

## Problem

`/v1/suggest` and `/v1/suggest/all` are single-pass LLM calls. Nothing checks
that the generated suggestions are genuinely useful: a suggestion can *sound*
right — fluent, confident, on-topic — while being generic filler or ungrounded
in the actual brief ("prompt-passing"). Those false positives erode trust in
the screener. The owner's requested shape:

```
while (!acceptable) {
  suggestions = generate(originalBrief, critiques)
  acceptable  = verify(suggestions)          // the verifier of the verifier
}
```

## Decisions (made with the project owner)

1. **Verifier target**: the quality of the *suggestions* (not a re-check of
   the brief's rule verdicts).
2. **Acceptability**: an LLM meta-judge rates each suggestion on three
   criteria — *anchored* (references content actually in this brief),
   *on-rule* (addresses what the failing rule requires), *actionable*
   (author can act without guessing; generic fluff is rejected).
3. **Loop home**: server-side, inside `suggest`/`suggest_all`, max
   **2 retries** (3 generations total); rejected suggestions are regenerated
   with the rejection reasons fed back; accepted ones are kept.
4. **Models** (cost-first; owner decision 2026-07-16):
   - judge + suggester: `deepseek/deepseek-v4-pro` ($0.43/$0.87 per MTok)
   - verifier: `deepseek/deepseek-v4-flash` ($0.10/$0.20 per MTok)
   - The `PB_VERIFIER_MODEL=auto` rule (first allowlist model with a
     different vendor prefix than the judge) stays implemented so a one-line
     env change restores cross-lab review; the deliberate tradeoff (cost over
     cross-lab decorrelation) is recorded in ADR 0001/0002.

## Architecture

Respecting the seam invariant (LLM returns verdicts; deterministic code owns
every decision):

- **`perfect_brief/llm.py`** (engine, zero service deps):
  - `render_review_prompt(rules_subset, brief, suggestions, locale)` — asks
    the verifier to accept/reject each suggestion per the three criteria.
  - `parse_review(raw)` → `{rule_id: {"accepted": bool, "reason": str}}`.
  - `render_suggest_prompt` / `render_suggest_all_prompt` gain an optional
    `critiques: dict[rule_id, str]` parameter (rejection reasons appended).
- **`app/scorer.py`** (orchestration): the loop, the deterministic sanity
  screen (non-empty, sane length, valid rule id), the accept/stop policy,
  caching, graceful degradation.
- **`app/settings.py`**: `PB_VERIFIER_MODEL` (explicit slug, or `auto` =
  first allowlist model whose vendor prefix differs from the judge's; falls
  back to the judge model when the allowlist has one vendor, flagged in the
  response).
- **`app/llm_client.py`**: per-model quirk — omit sampling params for models
  that reject non-default values (e.g. Claude 4.7+/5 family) instead of
  sending `temperature: 0`.

## Data flow (`suggest` and `suggest_all`)

1. Generate suggestions (judge model, existing prompts, optional critiques).
2. Deterministic sanity screen in code.
3. Verifier pass (verifier model): per-suggestion accept/reject + reason.
4. Any rejected + retries left (≤2): regenerate *only rejected rules* with
   critiques; keep accepted ones.
5. Return all suggestions; each carries `review: {accepted, reason}`;
   response gains `screened` (true iff all accepted), `iterations`,
   `verifier_model`. Additive — no consumer breaks.
6. Cache the final set: `pb:s:{ruleset_version}:{judge_model}:{verifier_model}:{sha256(brief)}:{rule_ids}`
   with the existing TTL (suggestions have no cache today; the loop makes one
   worthwhile).

## Error handling

The screener must never break suggestions: verifier call fails or parse error
→ return generated suggestions with `screened: false` + `warning`. Mock judge
path gets a deterministic accept-all `MockReviewer` so `make test` stays
offline-green. BYOK (`X-LLM-Key`) funds both passes (OpenRouter: one key, all
models); never stored or logged (existing invariant).

## Cost (measured prompts, live OpenRouter prices, 2026-07-16)

Score $0.0015 · suggest single-pass $0.0014 (verify adds $0.0003) · suggest
worst-case $0.0042. Monthly at 70/25/5 casual/engaged/heavy mix: 100 testers
≈ $0.75, 1k ≈ $7.50, 10k ≈ $75. Hard ceiling = OpenRouter key spend cap;
redis rate limiter + suggestion cache bound abuse; BYOK bills the caller.

## Testing

Scoring untouched → all fixtures stay green by construction. New tests:
`parse_review` round-trip; loop convergence (stub reviewer rejects once, then
accepts); best-effort exit after max retries; degradation when reviewer
raises; verifier model resolution (`auto` picks different vendor; explicit
slug wins; single-vendor allowlist falls back + flags).

## Console (surgical edit only)

Badge on suggestions: "verified by <model>" when `screened`, muted
"unverified" otherwise.

## OSS documentation (part of the deliverable)

- `docs/decisions/0001-cross-model-verification.md` — why a second model
  reviews the first (LLM self-preference bias), the cross-lab/cultural
  option, and why we currently run same-lab (cost).
- `docs/decisions/0002-default-model-selection.md` — selection criteria,
  date-stamped price/benchmark snapshot, revisit policy (re-check when
  Sonnet 5 intro pricing ends 2026-08-31 and at each ruleset major bump).
- README section linking both.

## Env (already applied, this commit)

`PB_OPENROUTER_MODELS=deepseek/deepseek-v4-pro,deepseek/deepseek-v4-flash`
and `PB_VERIFIER_MODEL=deepseek/deepseek-v4-flash` in `.env.dev`,
`.env.staging`, `.env.production`; production switched from the legacy
`PB_ANTHROPIC_API_KEY`/`PB_MODEL` pattern to the OpenRouter pattern (the
prod 1Password item, not yet created, needs field `PB_OPENROUTER_API_KEY`).
