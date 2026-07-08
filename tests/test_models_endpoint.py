"""Model allowlist: /v1/models shape and per-request validation."""

from app import llm_client
from app.settings import Settings


def test_models_endpoint_shape(client):
    data = client.get("/v1/models").json()
    assert data["available"] and data["default"] == data["available"][0]
    assert data["llm_configured"] is False  # test env has no keys


def test_openrouter_allowlist_parsing(monkeypatch):
    stub = Settings(
        openrouter_api_key="or-test",
        openrouter_models=" anthropic/claude-sonnet-4.5 , openai/gpt-4o ,",
    )
    monkeypatch.setattr(llm_client, "settings", lambda: stub)
    assert llm_client.available_models() == ["anthropic/claude-sonnet-4.5", "openai/gpt-4o"]
    assert llm_client.default_model() == "anthropic/claude-sonnet-4.5"
    assert llm_client.resolve_model(None) == "anthropic/claude-sonnet-4.5"
    assert llm_client.resolve_model("openai/gpt-4o") == "openai/gpt-4o"


def test_disallowed_model_rejected(monkeypatch):
    stub = Settings(openrouter_api_key="or-test", openrouter_models="anthropic/claude-sonnet-4.5")
    monkeypatch.setattr(llm_client, "settings", lambda: stub)
    import pytest

    with pytest.raises(llm_client.ModelNotAllowed):
        llm_client.resolve_model("openai/gpt-4o")


def test_score_with_disallowed_model_is_422(client, monkeypatch):
    stub = Settings(openrouter_api_key="or-test", openrouter_models="anthropic/claude-sonnet-4.5")
    monkeypatch.setattr(llm_client, "settings", lambda: stub)
    r = client.post(
        "/v1/score",
        json={"brief": "# T\nProblem: x. Budget 15k.", "judge": "llm", "model": "not/enabled"},
    )
    assert r.status_code == 422
    assert "not enabled" in r.json()["detail"]
