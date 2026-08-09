# Security policy

## Reporting a vulnerability

Please report vulnerabilities privately — not in a public issue:

- **Preferred:** [GitHub private vulnerability reporting](https://github.com/welance/perfect-brief/security/advisories/new)
- **Email:** security@welance.com

Include what you found, where (file/endpoint), and how to reproduce it. We
acknowledge reports within a week and keep you posted until it's resolved.
Coordinated disclosure: give us reasonable time to ship a fix before
publishing details.

## Scope

- The service (`app/`): API endpoints, rate limiting, CORS, caching.
- The engine (`perfect_brief/`): the judge seam — the model must never see
  weights or decide the number; anything that lets model output touch the
  score, the gate, or the decision directly is a vulnerability here, not a
  feature request.
- The consoles (`app/static/`, `site/`): anything that exfiltrates a
  user-supplied key (the optional bring-your-own-key field) or executes
  untrusted brief content.

## Keys and secrets

No real secret ever belongs in this repository. LLM keys are server-side
environment variables (`PB_ANTHROPIC_API_KEY` / `PB_OPENROUTER_API_KEY`);
tracked `.env.*` files hold only deploy placeholders resolved outside git. A
caller-supplied `X-LLM-Key` is used per request and never stored or logged —
a code path that stores, logs, or echoes it is a valid report.

That last sentence is a claim, so it is also a test. `tests/test_byok_leak.py`
drives a real `/v1/score` request with a sentinel key and fails unless the
sentinel appears in exactly one place: the `Authorization` header of the
outbound provider call. Not in a log record, not in the response body or
headers, not in anything handed to Redis. If you are reviewing this area,
start there — and if you can make it pass while still leaking the key, that
itself is the report we want.

The reasoning behind each of those assertions, written for a reader who does
not want to read Python, is at [briefs.welance.com/security.html](https://briefs.welance.com/security.html)
(source: `site/security.html`).

## Supported versions

The `main` branch. There are no maintained release lines yet.
