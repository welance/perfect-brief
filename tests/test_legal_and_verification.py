"""What the directories check before listing the connector.

Claude's connectors directory and OpenAI's plugin review both want a privacy
policy and (OpenAI) terms at stable URLs, and OpenAI proves domain ownership
by fetching a token from /.well-known/openai-apps-challenge.
"""

from __future__ import annotations

import pytest

from app.settings import settings

CHALLENGE = "/.well-known/openai-apps-challenge"


@pytest.mark.parametrize("path", ["/privacy.html", "/privacy", "/terms.html", "/terms", "/it/privacy"])
def test_the_legal_pages_answer_at_every_spelling(client, path):
    r = client.get(path)
    assert r.status_code == 200, path
    assert r.headers["content-type"].startswith("text/html")
    assert "hello@welance.com" in r.text


def test_the_privacy_page_names_the_operators_and_the_sub_processor(client):
    text = client.get("/privacy").text
    for fact in (
        "welance ventures GmbH",
        "welance ventures Italia S.R.L.",
        "OpenRouter",
        "24 hours",
        "SHA-256",
    ):
        assert fact in text, fact


def test_a_clean_url_never_shadows_a_file(client):
    assert client.get("/llms.txt").status_code == 200
    assert client.get("/no-such-page").status_code == 404


def test_the_footer_links_both_pages():
    from app.main import SITE

    chrome = (SITE / "chrome.js").read_text()
    assert 'href="privacy.html"' in chrome and 'href="terms.html"' in chrome


@pytest.fixture
def challenge(monkeypatch):
    def set_token(value: str | None):
        if value is None:
            monkeypatch.delenv("PB_OPENAI_APPS_CHALLENGE", raising=False)
        else:
            monkeypatch.setenv("PB_OPENAI_APPS_CHALLENGE", value)
        settings.cache_clear()

    yield set_token
    monkeypatch.delenv("PB_OPENAI_APPS_CHALLENGE", raising=False)
    settings.cache_clear()


def test_the_openai_challenge_is_absent_until_configured(client, challenge):
    challenge(None)
    assert client.get(CHALLENGE).status_code == 404
    challenge("   ")
    assert client.get(CHALLENGE).status_code == 404


def test_the_openai_challenge_is_the_token_as_plain_text(client, challenge):
    challenge("tok_abc123")
    r = client.get(CHALLENGE)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    assert r.text == "tok_abc123"
