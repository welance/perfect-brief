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


def test_byok_header_enables_llm_judge(client, monkeypatch):
    async def fake_complete(prompt, model=None, api_key=None):
        assert api_key == "sk-or-user-key"
        return '[{"rule_id":"clear-title","status":"pass","confidence":0.9,"quote":"t","note":""}]'

    monkeypatch.setattr(llm_client, "complete", fake_complete)
    body = {"brief": "# T\nProblem: x. Budget 15k.", "judge": "llm"}
    # without a key and with no server key configured: 503
    assert client.post("/v1/score", json=body).status_code == 503
    # with a caller key: the judge runs, and the resolved model is recorded
    r = client.post("/v1/score", json=body, headers={"x-llm-key": "sk-or-user-key"})
    assert r.status_code == 200
    data = r.json()
    assert data["judge"] == "llm" and data["model"]


def test_score_with_disallowed_model_is_422(client, monkeypatch):
    stub = Settings(openrouter_api_key="or-test", openrouter_models="anthropic/claude-sonnet-4.5")
    monkeypatch.setattr(llm_client, "settings", lambda: stub)
    r = client.post(
        "/v1/score",
        json={"brief": "# T\nProblem: x. Budget 15k.", "judge": "llm", "model": "not/enabled"},
    )
    assert r.status_code == 422
    assert "not enabled" in r.json()["detail"]
