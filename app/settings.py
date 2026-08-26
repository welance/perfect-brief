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
    # vendor-prefixed — e.g. "deepseek/deepseek-v4-pro,deepseek/deepseek-v4-flash").
    # First entry is the default when OpenRouter is active. Empty = PB_MODEL only.
    openrouter_models: str = ""
    # Operator policy for caller-supplied OpenRouter keys, and the only fence
    # that makes "never a lab model" true rather than merely intended.
    #
    # It used to default to empty — unrestricted — with a comment saying
    # Welance tiers pin it. A guarantee that depends on every deployment
    # remembering to set an env var is not a guarantee: the default IS the
    # policy, and a tier that wants something else can still say so.
    #
    # BYOK is exactly where this matters. A caller brings a key and names a
    # model, and without an allowlist the service will faithfully spend that
    # key on the most expensive tier on OpenRouter.
    byok_models: str = (
        "deepseek/deepseek-v4-pro,deepseek/deepseek-v4-flash,"
        "google/gemini-3.5-flash-lite,google/gemini-3.1-flash-lite,"
        "openai/gpt-5-nano,anthropic/claude-haiku-4.5"
    )
    # Suggestions are interactive draft generation, separate from published
    # scoring. The multilingual production-shaped eval selects Gemini 3.1
    # Flash-Lite; the authoritative judge remains DeepSeek V4 Pro.
    suggest_model: str = "google/gemini-3.1-flash-lite"
    # Verifier for the suggestion loop: explicit slug, or "auto" = first
    # allowlist model whose vendor prefix differs from the judge's (falls back
    # to a different same-vendor model, then to the judge itself).
    # The all-gaps endpoint still uses this verifier. The interactive
    # single-rule path only does so when PB_SUGGEST_VERIFY=true.
    verifier_model: str = "deepseek/deepseek-v4-flash"
    # Single-rule suggestions are editable choices, not an authoritative
    # verdict. A second LLM pass doubled their latency without even catching a
    # wrong-language response. Keep it available for conservative deployments;
    # the scored/published brief still uses the full judge independently.
    suggest_verify: bool = False
    # OpenRouter otherwise prioritises price. Suggestions are interactive, so
    # route them using recent provider latency telemetry.
    suggest_provider_sort: str = "latency"
    # The judge that produces a published score. DeepSeek V4 Pro by operator
    # policy, and a DeepSeek slug for a second reason: this default is what a
    # caller gets when it supplies a key and names no model, and an
    # Anthropic-DIRECT id handed to OpenRouter is one that provider has never
    # heard of. p007-16's suggestion proxy did exactly that and every call
    # failed upstream, silently, for as long as nobody looked.
    model: str = "deepseek/deepseek-v4-pro"
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
    # Output ceilings are task-specific: suggestions are short JSON, while the
    # all-gaps endpoint may return one sentence for every rule.
    suggest_max_tokens: Annotated[int, Field(ge=200, le=8_000)] = 800
    suggest_all_max_tokens: Annotated[int, Field(ge=500, le=16_000)] = 2000
    verifier_max_tokens: Annotated[int, Field(ge=200, le=8_000)] = 800

    # OpenRouter's unified reasoning control, kept as a knob and DEFAULTED OFF.
    # "low" made V4 Pro slower, while "none" made the same live score complete
    # in 15.97s versus no HTTP response inside 90s at the provider default.
    # Welance tiers therefore set "none"; empty remains a self-hoster option.
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


def locale_name(locale: str) -> str | None:
    """Resolve both shipped base locales and browser region variants.

    The website correctly sends values such as ``it-IT`` and ``de-DE``.
    Previously those missed this exact-key table and removed the language
    instruction from the prompt altogether.
    """
    clean = locale.strip()
    if clean in LOCALE_NAMES:
        return LOCALE_NAMES[clean]
    base = clean.split("-", 1)[0].lower()
    return LOCALE_NAMES.get(base)
