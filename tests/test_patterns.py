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


# A numeric exclusion must never hide a real phone: a missed phone is a leak,
# a false positive is an edit. Every one of these is still a phone.
HIDDEN = [
    ("347 123 4567 €", "347 123 4567"),
    ("€ 3471234567", "3471234567"),
    ("cf 3471234567", "3471234567"),
    ("cf 347 123 4567", "347 123 4567"),
    ("questo nip 3471234567", "3471234567"),
    ("nip 347 123 4567", "347 123 4567"),
    ("P.IVA 347 123 4567", "347 123 4567"),
    ("tel. 02 1234567 - 5000 €", "02 1234567"),
    ("+39 347 1234567 (budget 3000 - 5000 €)", "+39 347 1234567"),
    ("tel. 02 - 1234567", "02 - 1234567"),
    ("02 / 1234567", "02 / 1234567"),
    ("347 - 123 4567", "347 - 123 4567"),
    ("02 1234 / 5678", "02 1234 / 5678"),
    ("030 / 123 / 45678", "030 / 123 / 45678"),
]


@pytest.mark.parametrize("text,phone", HIDDEN)
def test_exclusions_fail_closed(text, phone):
    py = [[s.kind, s.text] for s in patterns.contact_spans(text)]
    js = harness.run_node(patterns.CATALOGUE_PATH, {"t": text})["t"]["spans"]
    assert ["phone", phone] in py
    assert [[k, t] for k, _, _, t in js] == py


@pytest.mark.parametrize(
    "text",
    [
        "tra 3000 - 5000 €",
        "10000 - 30000 €",
        "12-10-2026",
        "P.IVA 12345678901",
        "P.IVA 01234567890",
        "3000 €",
    ],
)
def test_amounts_and_tax_ids_are_still_not_phones(text):
    assert patterns.contact_spans(text) == []
    assert harness.run_node(patterns.CATALOGUE_PATH, {"t": text})["t"]["spans"] == []


# Whatever follows a phone — a year, a range, a currency — never hides it: the
# runtimes back off to the longest valid prefix instead of dropping the match.
SUFFIXES = [" / 2024", " - 5000 €", " 2026", " – 30000 €", " €", "/5"]
MUST_DETECT = sorted(
    {t for c in json.loads(patterns.CASES_PATH.read_text())["cases"] for k, t in c["spans"] if k == "phone"}
)


def _covers(spans, text, phone):
    at = text.index(phone)
    return any(k == "phone" and s <= at and e >= at + len(phone) for k, s, e, *_ in spans)


def test_a_suffix_never_hides_a_phone():
    texts = {f"{p}|{x}": p + x for p in MUST_DETECT for x in SUFFIXES}
    js = harness.run_node(patterns.CATALOGUE_PATH, texts)
    missed = []
    for key, text in texts.items():
        phone = key.split("|")[0]
        py = [[s.kind, s.start, s.end] for s in patterns.contact_spans(text)]
        for engine, spans in (("python", py), ("node", js[key]["spans"])):
            if not _covers(spans, text, phone):
                missed.append((engine, text))
    assert not missed, missed


# Subject spans say where a brief already states its budget or timeline, so a
# consumer can show it instead of asking again. Presence only, never a verdict.
LISTING = "Città: Milano · Full remote\nDurata stimata: qualche mese o anno\nBudget: tra 3000 - 5000 €"


def test_subject_spans_read_a_listing_on_both_engines():
    py = [[s.subject, s.start, s.end, s.text] for s in patterns.subject_spans(LISTING)]
    assert [[k, t] for k, _, _, t in py] == [
        ["timeline", "qualche mese o anno"],
        ["budget", "tra 3000 - 5000 €"],
    ]
    assert all(LISTING[s:e] == t for _, s, e, t in py)
    assert harness.run_node(patterns.CATALOGUE_PATH, {"t": LISTING})["t"]["subjects"] == py


@pytest.mark.parametrize(
    "text",
    ["Budget 2026: da definire", "Il prodotto costa 3000 €", "sconto del 30 %", "Budget: 347 123 4567"],
)
def test_unlabelled_or_non_monetary_numbers_are_not_budgets(text):
    assert [s for s in patterns.subject_spans(text) if s.subject == "budget"] == []
    assert harness.run_node(patterns.CATALOGUE_PATH, {"t": text})["t"]["subjects"] == []


def test_subject_spans_do_not_change_contact_detection():
    # the subjects section is additive: dropping it leaves every contact span as is
    data = json.loads(patterns.CATALOGUE_PATH.read_text())
    without = patterns.Catalogue({**data, "subjects": []})
    for case in json.loads(patterns.CASES_PATH.read_text())["cases"]:
        assert without.contact_spans(case["text"]) == patterns.contact_spans(case["text"]), case["id"]


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
        for _, rx in cat.contacts + cat.exclusions + cat.subjects:
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
