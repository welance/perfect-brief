# The Operator Covenant

Every rule in this repository judges *briefs*. This file judges *us*.

It exists because of a conflict of interest we would rather name than manage
quietly: welance wrote this bar, welance operates **welance/Directory** — the
noticeboard this bar gates — and welance **also pitches as a team on that
noticeboard**, at the same fees, behind the same anonymity, judged by the same
rules. Judge, gatekeeper, and contestant. Openness is the structural answer
(a public, versioned, fixture-guarded bar cannot be tuned quietly), but
openness constrains the *bar*. This covenant constrains the *operator*.

The commitments below bind welance in how it runs the public service at
`briefs.welance.com` and in what it does with what that service sees. They are
listed with their enforcement status, because a promise that says how it is
checked is worth more than a promise that says how much it is meant.

## What we commit to

1. **We never mine briefs for leads.** No brief sent to this service is read,
   aggregated, or acted on commercially. Nobody at welance contacts a person,
   a company, or a market because of what a scored brief contained.
2. **We never train on briefs.** No brief, verdict, or suggestion output is
   used to train or fine-tune any model, by us or on our instruction.
3. **We keep nothing beyond the mechanism.** The service is stateless: no
   database, no accounts. What exists is a 24-hour verdict cache (status,
   confidence, a short verbatim quote, keyed by a hash of the brief — honoured
   off by `no_cache: true`, always skipped for bring-your-own-key calls) and
   per-IP rate counters that expire with their window.
4. **Nothing you send reaches our logs.** Access logs carry client address,
   request line, and status — never request bodies, never headers, never keys.
   We cap access-log retention at 30 days.
5. **No human browses the cache.** Redis access is operational (deploy,
   debug, expiry) — not a reading room. Cached verdicts are never exported,
   queried for content, or joined with anything.
6. **welance's own briefs pass the same bar.** Same gate, same model, same
   `ruleset_version` — and because every verdict carries that version, anyone
   can check that no brief, ours included, was judged against a private bar.
7. **The fees stay at cost.** The platform layer is priced to cover the rails,
   never as a profit centre; welance earns by winning work on the field, not
   at the tollbooth, and says so publicly.
8. **This covenant changes like a rule changes.** Any edit to this file is a
   public PR, versioned with the repository — never a quiet rewrite.

## How each commitment is enforced

| # | Commitment | Enforcement today |
|---|-----------|-------------------|
| 3 | key never stored/logged/cached | **CI-tested**: [`tests/test_byok_leak.py`](tests/test_byok_leak.py) plants a canary key and fails the build if it reaches any log record, stdout/stderr, response body, response header, or anything handed to Redis |
| 3 | cache holds verdicts only, 24h TTL, `no_cache` honoured, BYOK bypasses cache | **in code**, reviewable: `app/scorer.py`, `app/cache.py` |
| 4 | no bodies in logs | log format is code, reviewable; a brief-body canary test in the style of the key canary is the next planned test |
| 1, 2, 5 | no mining, no training, no reading room | **not mechanically enforceable — we run the servers.** Stated here, versioned, and falsifiable by whistle: if you ever receive contact from welance that could only be explained by a brief you scored, that is a covenant breach — report it publicly or to security@welance.com |
| 6 | same bar for welance's briefs | **verifiable by design**: `ruleset_version` + model on every verdict; the scoring engine has no caller-identity input to discriminate on (`perfect_brief/` takes text, nothing else) |
| 7 | fees at cost | to be evidenced by a published running-cost ledger (planned; until it exists, this line is a promise, not a proof) |

## The honest limit

Commitments 1, 2 and 5 cannot be proven from outside — you would have to
trust that the deployed code is this code and that nobody looks. We will not
pretend otherwise. Three things narrow the gap: the architecture keeps almost
nothing worth mining (24 hours of verdict rows), the parts that *can* be
tested fail the build when violated, and the whole service is MIT-licensed —
`make up` runs it on your machine, where no trust in us is required at all.
For anything genuinely confidential, that is the honest recommendation, and
it costs you nothing.

## Scope

This covenant covers the public service at `briefs.welance.com` and any
welance-operated deployment of this repository, including future endpoints
that see brief-shaped content (e.g. a drafting endpoint). It does not bind
third parties: model providers' retention is governed by their terms
(see [data.html](site/data.html)), and self-hosted copies are their
operators' responsibility.
