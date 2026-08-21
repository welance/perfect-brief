"""Runtime configuration, read from environment (see .env.example)."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field
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
    # Optional operator policy for caller-supplied OpenRouter keys. Empty keeps
    # public BYOK unrestricted; Welance tiers pin this to the two DeepSeek V4
    # models so an internal proxy cannot accidentally select an expensive lab.
    byok_models: str = ""
    # Suggestions are cheaper extraction/generation work than final scoring.
    # Empty inherits the default judge; Welance tiers explicitly use V4 Flash.
    suggest_model: str = ""
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
    llm_max_tokens: Annotated[int, Field(ge=500, le=32_000)] = 4000

    # OpenRouter's unified reasoning control, kept as a knob and DEFAULTED OFF.
    # Asking deepseek-v4-pro for effort "low" made the call slower, not cheaper:
    # measured on develop, three runs at ~50s and cut at the edge, against ~28s
    # for the same brief with no reasoning field at all. Empty sends no field.
    llm_reasoning_effort: str = ""
    # 0 keeps the legacy single call. A positive value partitions the rules
    # into deterministic batches and runs them with bounded concurrency.
    judge_batch_size: Annotated[int, Field(ge=0, le=14)] = 0
    judge_concurrency: Annotated[int, Field(ge=1, le=14)] = 3
    llm_timeout_seconds: Annotated[float, Field(ge=1, le=300)] = 120.0

    # Redis (verdict cache + rate limit)
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: Annotated[int, Field(ge=1, le=604_800)] = 86_400

    # Policy
    default_judge: str = "mock"  # "mock" | "llm"
    rate_limit_per_minute: Annotated[int, Field(ge=0, le=100_000)] = 60  # 0 disables
    paid_llm_rate_limit_per_minute: Annotated[int, Field(ge=0, le=10_000)] = 10
    request_max_chars: Annotated[int, Field(ge=100, le=1_000_000)] = 20_000
    byok_max_chars: Annotated[int, Field(ge=64, le=4096)] = 512
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
