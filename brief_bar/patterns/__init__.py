"""Deterministic spans and cues from the shared pattern catalogue.

`catalogue.json` is data, owned here and vendored by consumers (the Directory's
pre-publish scan runs the same file through `runtime.mjs`). This module and
`runtime.mjs` implement one contract and are held to it by the dual-engine
harness (`python -m experiments.pattern_harness`) over `cases.json`:

  1. Every contact pattern runs over the ORIGINAL text. Group 1, when present,
     is the span (it must end where the match ends — the leading part is a
     boundary, since lookbehind is not portable).
  2. A phone candidate is valid when its digit count is within its pattern's
     limits and no exclusion hides it. An exclusion hides it only when it
     covers the whole candidate and carries no other digits (it is about
     exactly this number). Patterns with `never_excluded_from_digits` (a + /
     00 prefix, a full Italian mobile) are never hidden; patterns with
     `hidden_only_by_structural` (national numbers) yield only to
     `structural` exclusions (dates, tax ids, IBANs), never to amounts.
     An invalid candidate BACKS OFF: it is cut at the end of each digit run,
     longest first, and the first prefix the pattern still matches exactly
     and that is valid is kept. So "030 12345678 / 2024" keeps
     "030 12345678": what follows a phone never hides it. A missed phone is a
     privacy leak; a false positive is an edit, so ambiguity fails closed.
  3. Overlaps resolve by priority, then the longer span, then the earlier
     start, then the pattern id. Spans come back in document order.
  4. Keyword cues are lowercase substrings of the lowercased text.

No LLM runs here, ever; the offline improvement loop only proposes edits to
the catalogue and the corpus for human review.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent
CATALOGUE_PATH = _DIR / "catalogue.json"
CASES_PATH = _DIR / "cases.json"


@dataclass(frozen=True)
class Span:
    kind: str
    start: int
    end: int
    text: str
    pattern: str


def _compile(entry: dict) -> re.Pattern[str]:
    return re.compile(entry["source"], re.IGNORECASE if "i" in entry.get("flags", "") else 0)


def _span(m: re.Match[str]) -> tuple[int, int]:
    if m.re.groups and m.group(1) is not None:
        return m.span(1)
    return m.span()


def _digits(s: str) -> int:
    return sum("0" <= c <= "9" for c in s)


class Catalogue:
    def __init__(self, data: dict):
        self.data = data
        self.version: str = data["version"]
        self.contacts = [(e, _compile(e)) for e in data["contacts"]]
        self.exclusions = [(e, _compile(e)) for e in data["exclusions"]]
        self.keywords: dict[str, list[str]] = data["keywords"]

    def exclusion_spans(self, text: str) -> list[tuple[int, int, bool]]:
        return [
            (*_span(m), bool(e.get("structural"))) for e, rx in self.exclusions for m in rx.finditer(text)
        ]

    @staticmethod
    def _hidden(e: dict, s: int, end: int, text: str, excluded: list[tuple[int, int, bool]]) -> bool:
        n = _digits(text[s:end])
        if n >= e.get("never_excluded_from_digits", n + 1):
            return False
        return any(
            xs <= s
            and end <= xe
            and _digits(text[xs:xe]) == n
            and (structural or not e.get("hidden_only_by_structural"))
            for xs, xe, structural in excluded
        )

    def _valid(self, e: dict, s: int, end: int, text: str, excluded: list[tuple[int, int, bool]]) -> bool:
        if "min_digits" in e and not e["min_digits"] <= _digits(text[s:end]) <= e["max_digits"]:
            return False
        return not (e["kind"] == "phone" and self._hidden(e, s, end, text, excluded))

    def _back_off(self, e, rx, m, text, excluded) -> tuple[int, int] | None:
        """The longest valid prefix of a match, cut where a digit run ends."""
        s, end = _span(m)
        if self._valid(e, s, end, text, excluded):
            return s, end
        if "min_digits" not in e:
            return None
        for k in range(end - 1, s, -1):
            if not ("0" <= text[k - 1] <= "9") or "0" <= text[k] <= "9":
                continue
            mm = rx.match(text[:k], m.start())
            if mm and _span(mm) == (s, k) and self._valid(e, s, k, text, excluded):
                return s, k
        return None

    def contact_spans(self, text: str) -> list[Span]:
        excluded = self.exclusion_spans(text)
        cands: list[tuple[dict, int, int]] = []
        for e, rx in self.contacts:
            for m in rx.finditer(text):
                kept_span = self._back_off(e, rx, m, text, excluded)
                if kept_span:
                    cands.append((e, *kept_span))
        cands.sort(key=lambda c: (-c[0]["priority"], -(c[2] - c[1]), c[1], c[0]["id"]))
        kept: list[tuple[dict, int, int]] = []
        for c in cands:
            if not any(c[1] < k[2] and c[2] > k[1] for k in kept):
                kept.append(c)
        kept.sort(key=lambda c: c[1])
        return [Span(e["kind"], s, end, text[s:end], e["id"]) for e, s, end in kept]

    def keyword_hits(self, text: str, group: str) -> list[str]:
        t = text.lower()
        return [k for k in self.keywords[group] if k in t]


def load(path: str | Path = CATALOGUE_PATH) -> Catalogue:
    with open(path, encoding="utf-8") as fh:
        return Catalogue(json.load(fh))


@lru_cache(maxsize=1)
def bundled() -> Catalogue:
    return load()


def contact_spans(text: str) -> list[Span]:
    return bundled().contact_spans(text)
