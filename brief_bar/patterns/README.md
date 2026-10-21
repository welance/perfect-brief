# Pattern catalogue

`catalogue.json` is the one deterministic answer to "is this an email, a URL,
a phone number, or personal data?" for the offline judge here and for the
Directory's pre-publish scan (welance.com vendors a pinned copy of
`catalogue.json` + `runtime.mjs`). No LLM runs at request time.

| File | Role |
|---|---|
| `catalogue.json` | contact patterns, phone exclusions, subject patterns, data/compliance keywords — data, versioned |
| `__init__.py` | Python runtime (the mock judge) |
| `runtime.mjs` | JavaScript runtime (browsers, Node) — same contract |
| `cases.json` | labelled corpus: `spans` as `[kind, text]` in document order, optional `subjects` as `[subject, text]`, optional `data` / `compliance` cues |

The catalogue bytes are part of the ruleset digest (`loader.content_digest`),
so any edit moves `ruleset_version`.

## Contract

1. Contact patterns run over the original text. Group 1, when present, is
   the span and must end where the match ends (the leading part is a boundary,
   because lookbehind is not portable).
2. A phone candidate is valid when its digits are within `min_digits`..
   `max_digits` and no exclusion hides it. An exclusion hides it only when it
   covers the whole candidate and carries no other digits.
   `never_excluded_from_digits` patterns (a `+`/`00` prefix, a full Italian
   mobile) are never hidden; `hidden_only_by_structural` patterns (national
   numbers) yield only to `structural` exclusions (dates, tax ids, IBANs),
   never to amounts or ranges. An invalid candidate **backs off**: it is cut
   where each digit run ends, longest first, and the first prefix the pattern
   still matches exactly and that is valid is kept, so "030 12345678 / 2024"
   keeps "030 12345678". Exclusions never touch emails or URLs. A missed
   phone is a leak, a false positive is an edit: ambiguity fails closed.
   When you narrow a phone pattern, add the must-detect cases first.
3. Overlaps resolve by `priority`, then the longer span, then the earlier
   start, then the id. Spans come back in document order.
4. Keywords are lowercase substrings of the lowercased text.
5. Subject spans (`subject_spans` / `subjectSpans`) say where the text already
   states a subject: `budget` (a budget label, then an amount carrying a
   currency or multiplier, or a range) or `timeline` (a duration/deadline label
   and a colon, then the rest of the line). Group 1 is the value without its
   label, as `{subject, start, end, text, pattern}`. They report presence only —
   no floor, no comparison, no verdict — so a consumer can show "you said
   this" instead of asking again. A bare number after a label (`Budget 2026`)
   is not a budget. Overlaps: longer span, earlier start, id.

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
