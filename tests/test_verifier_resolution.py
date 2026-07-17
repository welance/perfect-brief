"""PB_VERIFIER_MODEL resolution: explicit slug wins; auto picks a different vendor; single-vendor falls back."""

from app import llm_client
from app.settings import settings


def _reset(monkeypatch, models: str, verifier: str):
    monkeypatch.setenv("PB_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("PB_OPENROUTER_MODELS", models)
    monkeypatch.setenv("PB_VERIFIER_MODEL", verifier)
    settings.cache_clear()


def test_auto_picks_other_vendor(monkeypatch):
    _reset(monkeypatch, "deepseek/deepseek-v4-pro,anthropic/claude-sonnet-5", "auto")
    assert llm_client.resolve_verifier_model("deepseek/deepseek-v4-pro") == "anthropic/claude-sonnet-5"


def test_auto_same_vendor_prefers_different_model(monkeypatch):
    _reset(monkeypatch, "deepseek/deepseek-v4-pro,deepseek/deepseek-v4-flash", "auto")
    assert llm_client.resolve_verifier_model("deepseek/deepseek-v4-pro") == "deepseek/deepseek-v4-flash"


def test_explicit_slug_wins(monkeypatch):
    _reset(monkeypatch, "deepseek/deepseek-v4-pro,deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-flash")
    assert llm_client.resolve_verifier_model("deepseek/deepseek-v4-pro") == "deepseek/deepseek-v4-flash"


def test_single_model_falls_back_to_judge(monkeypatch):
    _reset(monkeypatch, "deepseek/deepseek-v4-pro", "auto")
    assert llm_client.resolve_verifier_model("deepseek/deepseek-v4-pro") == "deepseek/deepseek-v4-pro"


def test_sampling_kwargs_omit_temperature_for_sonnet5():
    assert "temperature" not in llm_client._sampling_kwargs("anthropic/claude-sonnet-5")
    assert llm_client._sampling_kwargs("deepseek/deepseek-v4-pro") == {"temperature": 0}
