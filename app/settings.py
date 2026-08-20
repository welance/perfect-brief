"""Runtime configuration, read from environment (see .env.example)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PB_", env_file=".env", extra="ignore")

    # LLM judge / suggestions. Two providers; OpenRouter wins if both keys set.
    anthropic_api_key: str | None = None
    openrouter_api_key: str | None = None
    # Comma-separated OpenRouter slugs a request may pick from (exact slugs,
    # vendor-prefixed — e.g. "anthropic/claude-sonnet-4.5,openai/gpt-4o").
    # First entry is the default when OpenRouter is active. Empty = PB_MODEL only.
    openrouter_models: str = ""
    # Verifier for the suggestion loop: explicit slug, or "auto" = first
    # allowlist model whose vendor prefix differs from the judge's (falls back
    # to a different same-vendor model, then to the judge itself).
    verifier_model: str = "auto"
    model: str = "claude-sonnet-4-6"
    # Fourteen verdicts, each with a verbatim quote and a note, do not fit in
    # 1500 — production cut off mid-string at 1569 characters once the gateway
    # timeout stopped hiding it. A non-Latin script needs more tokens per
    # character again, so the ceiling is sized for the ruleset, not the sample.
    #
    # 4000 was still not enough: the judges are reasoning models, and their
    # thinking is billed against this same ceiling before a single character of
    # JSON appears. Measured on develop, one brief in a pair tripped 4000 while
    # its shorter sibling passed. Unused headroom costs nothing — only generated
    # tokens are billed — while a ceiling hit costs the whole call and a 503.
    llm_max_tokens: int = 8000

    # Redis (verdict cache + rate limit)
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 86_400  # verdicts are deterministic at temp 0

    # Policy
    default_judge: str = "mock"  # "mock" | "llm"
    rate_limit_per_minute: int = 60  # 0 disables
    request_max_chars: int = 20_000
    cors_origins: list[str] = ["*"]


@lru_cache(maxsize=1)
def settings() -> Settings:
    return Settings()


# locale code -> language name for LLM prompts (matches the console's shipped set)
LOCALE_NAMES = {
    "en-GB": "English (UK)",
    "it": "Italiano",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "ar": "العربية",
    "pt": "Português",
    "pt-BR": "Português (Brasil)",
    "nl": "Nederlands",
    "pl": "Polski",
    "zh-Hans": "中文（简体）",
    "ja": "日本語",
}
