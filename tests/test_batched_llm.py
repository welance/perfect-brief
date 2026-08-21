"""Live release gate: one judge call versus concurrent 5/5/4 batches.

Not part of offline CI. It intentionally spends four provider calls on one
known brief and prints timings for the release record. Run in develop with a
real server key before PB_JUDGE_BATCH_SIZE is enabled there or in production.
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

from app import llm_client, scorer
from app.settings import settings

pytestmark = pytest.mark.skipif(
    not (os.environ.get("PB_ANTHROPIC_API_KEY") or os.environ.get("PB_OPENROUTER_API_KEY")),
    reason="llm-only: batching quality needs a real judge",
)

BRIEF = """# Real-time availability for restaurant bookings

Problem: staff cannot update availability across channels in real time.
Users are shift managers working on mobile during service. Success means
cutting no-shows by 30% within two seasons. Deliverables are a booking widget,
an availability panel and notifications, each with observable acceptance
conditions. Native apps are out of scope for v1. Budget is EUR 25,000-40,000
over eight weeks for a full-stack developer and a designer. It integrates with
the existing booking provider. Risk: staff may not keep availability current;
test that assumption first. Booking history is personal data, processed under
GDPR contract basis with a DPA. The interface targets WCAG 2.2 AA.
"""


def _run(batch_size: int):
    os.environ["PB_JUDGE_BATCH_SIZE"] = str(batch_size)
    settings.cache_clear()
    llm_client._anthropic.cache_clear()
    started = time.monotonic()
    result = asyncio.run(scorer.score(BRIEF, "en-GB", "llm", no_cache=True))
    return result, time.monotonic() - started


def test_single_call_and_concurrent_batches_keep_the_same_gate(capsys):
    original = os.environ.get("PB_JUDGE_BATCH_SIZE")
    try:
        single, single_seconds = _run(0)
        batched, batched_seconds = _run(5)
    finally:
        if original is None:
            os.environ.pop("PB_JUDGE_BATCH_SIZE", None)
        else:
            os.environ["PB_JUDGE_BATCH_SIZE"] = original
        settings.cache_clear()
        llm_client._anthropic.cache_clear()

    print(
        f"single={single_seconds:.2f}s batched={batched_seconds:.2f}s "
        f"scores={single.score}/{batched.score}",
        file=capsys.disabled(),
    )
    assert batched.gate.passed == single.gate.passed
    assert batched.gate.missing == single.gate.missing
    assert batched.decision == single.decision
    assert abs(batched.score - single.score) <= 10
