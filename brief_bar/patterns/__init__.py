"""Deterministic spans and cues from the shared pattern catalogue.

`catalogue.json` is data, owned here and vendored by consumers (the Directory's
pre-publish scan runs the same file through `runtime.mjs`). This module and
`runtime.mjs` implement one contract and are held to it by the dual-engine
harness (`python -m experiments.pattern_harness`) over `cases.json`:

  1. Every contact pattern runs over the ORIGINAL text. Group 1, when present,
     is the span (it must end where the match ends — the leading part is a
     boundary, since lookbehind is not portable).
  2. A phone candidate whose digit count is outside its pattern's limits, or
     that overlaps an exclusion (amount, range, date, tax id, IBAN...), is
     dropped.
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

    def exclusion_spans(self, text: str) -> list[tuple[int, int, str]]:
        return [(*_span(m), e["id"]) for e, rx in self.exclusions for m in rx.finditer(text)]

    def contact_spans(self, text: str) -> list[Span]:
        excluded = self.exclusion_spans(text)
        cands: list[tuple[dict, int, int]] = []
        for e, rx in self.contacts:
            for m in rx.finditer(text):
                s, end = _span(m)
                if "min_digits" in e and not e["min_digits"] <= _digits(text[s:end]) <= e["max_digits"]:
                    continue
                if e["kind"] == "phone" and any(s < xe and end > xs for xs, xe, _ in excluded):
                    continue
                cands.append((e, s, end))
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
