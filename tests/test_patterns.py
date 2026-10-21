"""The shared pattern catalogue: both engines, the labelled corpus, the dialect.

Node is required (the JavaScript runtime is what the Directory ships); a
missing node fails here rather than skipping, because parity is the point.
"""

import hashlib
import json
import subprocess
import sys

import pytest

from brief_bar import loader, patterns
from experiments import pattern_harness as harness

BUDGETS = ["Budget: tra 3000 - 5000 €", "Budget: tra 10000 - 30000 €"]
PHONES = ["347 123 4567", "02 1234567", "+39 02 1234567"]


def test_harness_passes_on_both_engines():
    # a subprocess with a timeout: a catastrophic regex must fail, not hang CI
    proc = subprocess.run(
        [sys.executable, "-m", "experiments.pattern_harness", "--json"],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=harness.ROOT,
    )
    report = json.loads(proc.stdout)
    assert report["ok"], json.dumps(
        {k: report[k] for k in ("invalid", "failures", "disagreements", "slow")}, indent=2
    )
    assert proc.returncode == 0


@pytest.mark.parametrize("text", BUDGETS)
def test_budget_ranges_are_not_phones(text):
    assert patterns.contact_spans(text) == []
    js = harness.run_node(patterns.CATALOGUE_PATH, {"t": text})
    assert js["t"]["spans"] == []


@pytest.mark.parametrize("text", PHONES)
def test_national_and_international_phones_are_found(text):
    py = [[s.kind, s.start, s.end, s.text] for s in patterns.contact_spans(text)]
    assert py == [["phone", 0, len(text), text]]
    assert harness.run_node(patterns.CATALOGUE_PATH, {"t": text})["t"]["spans"] == py


def test_sensitive_data_is_a_data_cue():
    cat = patterns.bundled()
    assert cat.keyword_hits("Protezione dei dati sensibili/biometrici.", "data")


@pytest.mark.parametrize(
    "source,needle",
    [
        (r"\d{3}", r"\d"),
        (r"(?<!x)a", "(?:"),
        (r"a.b", "unescaped '.'"),
        (r"ab$", "'$'"),
        (r"(a)\1", "backreferences"),
        (r"(?:ab)+", "unbounded repetition"),
        (r"(?:ab){2,}", "unbounded repetition"),
    ],
)
def test_dialect_rejects_non_portable_regex(source, needle):
    assert any(needle in e for e in harness.dialect_errors(source))


def test_dialect_accepts_the_portable_subset():
    assert harness.dialect_errors(r"(?:^|[^0-9.])([0-9]{1,3}(?:[.,][0-9]{3}){2,6})(?![0-9])") == []


def test_every_contact_capture_ends_where_the_match_ends():
    # runtime.mjs derives the span start from the match end; a group 1 that
    # ends early would give the two engines different offsets
    cat = patterns.bundled()
    for case in json.loads(patterns.CASES_PATH.read_text())["cases"]:
        for _, rx in cat.contacts + cat.exclusions:
            for m in rx.finditer(case["text"]):
                if rx.groups:
                    assert m.end(1) == m.end(), (rx.pattern, case["id"])


def test_catalogue_is_part_of_the_ruleset_digest():
    h = hashlib.sha256()
    data = loader._DATA
    for p in sorted((data / "rules").glob("*.yaml")) + [data / "scoring.yaml", patterns.CATALOGUE_PATH]:
        h.update(p.name.encode())
        h.update(p.read_bytes())
    assert loader.content_digest() == h.hexdigest()[:12]
    assert loader.semver() == "1.1.1"
