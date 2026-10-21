# Pattern catalogue

`catalogue.json` is the one deterministic answer to "is this an email, a URL,
a phone number, or personal data?" for the offline judge here and for the
Directory's pre-publish scan (welance.com vendors a pinned copy of
`catalogue.json` + `runtime.mjs`). No LLM runs at request time.

| File | Role |
|---|---|
| `catalogue.json` | contact patterns, phone exclusions, data/compliance keywords — data, versioned |
| `__init__.py` | Python runtime (the mock judge) |
| `runtime.mjs` | JavaScript runtime (browsers, Node) — same contract |
| `cases.json` | labelled corpus: `spans` as `[kind, text]` in document order, optional `data` / `compliance` cues |

The catalogue bytes are part of the ruleset digest (`loader.content_digest`),
so any edit moves `ruleset_version`.

## Contract

1. Contact patterns run over the original text. Group 1, when present, is
   the span and must end where the match ends (the leading part is a boundary,
   because lookbehind is not portable).
2. A phone candidate outside `min_digits`..`max_digits`, or overlapping an
   exclusion (amounts, ranges, grouped numbers, dates, tax ids, IBANs), is
   dropped. Exclusions never drop emails or URLs.
3. Overlaps resolve by `priority`, then the longer span, then the earlier
   start, then the id. Spans come back in document order.
4. Keywords are lowercase substrings of the lowercased text.

## Portable dialect

Python `re` and JavaScript `RegExp` (no `u` flag) agree on: literals, explicit
character classes, `(?:`, `(?=`, `(?!`, `^`, bounded `{m,n}`, `\uXXXX`, and the
`i` flag. Not allowed: `\d \w \s \b` and their negations, lookbehind, named
groups, backreferences, inline flags, unescaped `.`, `$`, and unbounded
repetition of a group (`(...)+`, `(...)*`, `(...){m,}`) — the last is how a
regex goes exponential.

## Changing it

    make test-patterns        # validate + both engines + adversarial timing

Add the failing text to `cases.json` first (`origin: "human"`), then change
the catalogue until both engines agree with every label. Bump `version` in
`catalogue.json` and the ruleset `VERSION`.

`make improve-patterns` (offline, paid, capped) asks an LLM to propose
catalogue edits and extra labelled cases, scores every proposal on this
harness, and writes the best candidate to `experiments/out/patterns/` for a
human to review. It never edits these files; see
`experiments/pattern_loop.py`.
