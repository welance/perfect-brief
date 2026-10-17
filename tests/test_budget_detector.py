"""The mock judge's budget detector must read European money formats.

Italian, German and French briefs write the currency symbol after the
number ("30.000–45.000 €"); a figure the live editor's offline judge
cannot see is reported as "no budget figure" and blocks the gate.
"""

import pytest

from brief_bar.judge import _budget_eur


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Budget band 25-40k for the v1 build.", 40_000),
        ("€30,000 over three months", 30_000),
        ("30.000 euro, tre mesi", 30_000),
        # Currency symbol after the number, Italian thousands separator.
        ("30.000–45.000 €, tre mesi", 45_000),
        ("45.000€", 45_000),
        ("Budget: 12 000 € sur trois mois", 12_000),
        ("Budget 40 k€", 40_000),
        ("ca. 35.000 EUR", 35_000),
    ],
)
def test_budget_detector_reads_european_formats(text, expected):
    assert _budget_eur(text) == expected


def test_budget_detector_ignores_prose_without_money():
    assert _budget_eur("twelve rooms, seventy covers, three months") is None
