# BYOK security explainer — design

**Date:** 2026-08-08
**Status:** approved, ready for planning

## The problem

`/v1/score` accepts `X-LLM-Key`: a caller's own OpenRouter key, forwarded to
the provider so the caller pays and can pick any model. Handing an `sk-` key to
someone else's server is the single most alarming thing this API asks of
anyone, and it is the first thing a security-minded reader will object to.

`site/data.html` already *asserts* the key is never stored or logged. Assertion
is precisely what a sceptical reader discounts. Nothing in the repository
*proves* it, and nothing *fails* if a future commit breaks it.

The goal is not to reassure. It is to make the claim checkable, and to be first
to name the parts that are genuinely uncomfortable.

## What the audit found

Traced 2026-08-08 against the tree at `860c0ec`.

The key's whole path: request header (`ByokHeader`, `app/main.py`) → function
argument through `scorer.score` → one `Authorization: Bearer` header on the
outbound OpenRouter call in `llm_client.complete` → discarded with the request
scope. It is never written to Redis, disk, a log statement, or a response body.

Four objections a reviewer will raise, and why each holds:

- **The 502 handler echoes exception text** (`post_score`, `app/main.py`:
  `detail=f"judge error: {exc}"`). The exception is httpx's `HTTPStatusError`,
  whose message carries status and URL only — never headers or request body.
- **`log.exception("scoring failed")` prints a traceback.** Python tracebacks
  carry source *lines*, not local values. What reaches the log is the literal
  source text `headers={"Authorization": f"Bearer {api_key or ...}"}` — the
  f-string, not its result.
- **Access logs.** uvicorn's default format is client address, request line,
  status (`Dockerfile` CMD, no custom log config). Headers and bodies never
  appear.
- **Browser.** `site/console.html`: `type="password"`, `autocomplete="off"`,
  held in a module-scope JS variable, never `localStorage`/`sessionStorage`.
  It dies on reload.

Two things the audit found that the current pages do **not** say:

1. **BYOK verdicts are cached on `/v1/score`.** The `if not api_key` guard
   exists only on the suggestion path (`scorer.suggest`). The verdict cache
   (`scorer._judge`) is keyed `pb:v:{version}:llm:{model}:{sha256(brief)}` — no
   key material is an input, so nothing about the key reaches Redis, but a BYOK
   call does read and write the shared verdict cache. `no_cache: true` is
   therefore load-bearing on `/v1/score`, not decorative.
2. **`cache.connect` logs `settings().redis_url` at INFO.** If that URL ever
   carries a password, the service's own secret lands in stdout on every boot.
   Not the caller's key — but a page inviting scrutiny makes this the first
   thing anyone greps for.

## Design

### 1. `site/security.html`

Six sections, at the site's existing quality bar:

1. **The claim, stated narrowly.** Not "your key is safe" (unfalsifiable) but
   "your key reaches exactly one destination, and here is every line that
   touches it."
2. **The path** — the four hops above, each with its code reference.
3. **Where it is not** — logs, cache, response, browser. Each gives the
   *reason* it cannot be there, not a promise that it isn't.
4. **"Don't trust the prose"** — the canary test, quoted inline.
5. **The honest limits** — TLS terminates on our box, so a compromised server
   *would* see the key in memory; that is inherent to any proxy and we will not
   pretend otherwise. Provider terms apply downstream. BYOK verdicts do hit the
   shared verdict cache unless `no_cache` is sent.
6. **What to do anyway** — spend-capped OpenRouter key, `no_cache`, or
   self-host.

### 2. i18n that cannot produce a false claim

The site carries 8 locales. Translated security prose that drifts from the code
is worse than none, so the page splits:

- **Translated:** narrative prose, section headings, the limits, the advice.
- **Never translated:** file paths, function names, code blocks, test names.
  These sit outside the i18n keys, in monospace, identical in every locale.

A stale translation can therefore soften a sentence, but can never contradict
the code it sits next to.

**Code references carry no line numbers.** Prose cites `function in file`; the
link is a permalink pinned to a release tag, re-pinned at release time. Line
numbers rot on the first refactor, and a citation that 404s costs more trust
than no citation.

### 3. `tests/test_byok_leak.py` — the canary

One sentinel value driven through a real `/v1/score` BYOK request, with the
httpx transport stubbed, Redis faked, and `caplog` at DEBUG. Assert the
sentinel appears in **exactly one** place — the `Authorization` header of the
outbound OpenRouter call — and in no log record, response body, response
header, or Redis write.

A second test forces a 401 from OpenRouter and asserts the sentinel is absent
from the resulting 502 body.

The value is not today's audit. It is that the test fails on the *future*
commit that adds well-meaning debug logging.

### 4. Two fixes in the same change

- `cache.connect` stops logging `redis_url`.
- `site/data.html` gains one clause: BYOK verdicts *are* cached on `/v1/score`
  unless `no_cache` is sent. Silence there reads as concealment once a security
  page exists.

### 5. Where it is linked

`site/data.html` (the BYOK section), `SECURITY.md`, the README BYOK line, and
the console's key field.

## Out of scope

Routing the browser console directly to OpenRouter so the key never reaches the
service. It is the strongest possible answer for web users, but it does nothing
for API, curl, and MCP callers, who must proxy regardless — so the page is
needed either way. Worth revisiting as its own change.

## Delivery

Classic git-flow: `feature/byok-security-explainer` → `develop` →
`release/*` → `master`. `develop` fast-forwards to `main` first (it is 0
commits ahead), restoring the twin sync that NOTES.md describes.
