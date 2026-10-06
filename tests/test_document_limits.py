"""The text guard must pass the entire document or refuse before the judge."""

from app import scorer
from app.settings import settings


def test_large_document_reaches_scorer_without_truncation(client, monkeypatch):
    original = scorer.score
    seen = []

    async def capture(brief, *args, **kwargs):
        seen.append(brief)
        return await original(brief, *args, **kwargs)

    monkeypatch.setattr(scorer, "score", capture)
    brief = "# Document\n" + "A requirement. " * 35_000 + "FINAL REQUIREMENT"
    response = client.post("/v1/score", json={"brief": brief, "judge": "mock", "no_cache": True})
    assert response.status_code == 200
    assert seen == [brief]


def test_oversized_text_never_reaches_scorer(client, monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("oversized document reached scorer")

    monkeypatch.setattr(scorer, "score", forbidden)
    limit = settings().request_max_chars
    response = client.post("/v1/score", json={"brief": "x" * (limit + 1), "judge": "mock"})
    assert response.status_code == 413
    assert str(limit) in response.json()["detail"]


def test_operator_can_keep_a_smaller_text_limit(client, monkeypatch):
    monkeypatch.setattr(settings(), "request_max_chars", 20_000)
    response = client.post("/v1/score", json={"brief": "x" * 20_001, "judge": "mock"})
    assert response.status_code == 413
