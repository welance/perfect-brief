"""Thin async wrapper around the judge's LLM provider.

Two providers, chosen by which key is present (OpenRouter wins if both):
- OpenRouter (OpenAI-compatible chat/completions) — enables per-request model
  choice, restricted to the PB_OPENROUTER_MODELS allowlist.
- Anthropic Messages API (direct) — single-model service via PB_MODEL.

Lazily imported so the mock judge (and the whole test suite) runs with no SDK
and no API key. Temperature is pinned to 0 for reproducibility; the resolved
model is part of the verdict cache key and the score response, because a
verdict is only reproducible against (ruleset_version, model).
"""

from __future__ import annotations

import logging
import re
import time
from functools import lru_cache

from .settings import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
log = logging.getLogger("perfect_brief.llm")
_openrouter_client = None
_openrouter_client_factory = None
_openrouter_client_timeout = None


class LLMNotConfigured(RuntimeError):
    pass


class ModelNotAllowed(LookupError):
    pass


class JudgeTruncated(RuntimeError):
    """The model stopped because it ran out of room, not because it was done.

    Both providers say so and both were being ignored: OpenRouter sends
    ``finish_reason: "length"``, Anthropic ``stop_reason: "max_tokens"``. A
    partial answer must never reach the scorer — missing verdicts default to
    not_applicable, which would quietly change the number.
    """


def _use_openrouter() -> bool:
    return bool(settings().openrouter_api_key)


def configured() -> bool:
    return bool(settings().openrouter_api_key or settings().anthropic_api_key)


def available_models() -> list[str]:
    """Models a request may pick from; the first entry is the default."""
    cfg = settings()
    if _use_openrouter():
        slugs = [m.strip() for m in cfg.openrouter_models.split(",") if m.strip()]
        return slugs or [cfg.model]
    return [cfg.model]


def default_model() -> str:
    return available_models()[0]


# Models that reject non-default sampling params (Claude 4.7+/5 family):
# for these, omit temperature entirely instead of pinning 0.
_NO_TEMP_MARKERS = ("claude-sonnet-5", "claude-opus-4.7", "claude-opus-4.8", "claude-fable")


def _sampling_kwargs(model: str) -> dict:
    if any(m in model for m in _NO_TEMP_MARKERS):
        return {}
    return {"temperature": 0}


def _reasoning_kwargs() -> dict:
    """Keep a reasoning model's thinking short; it is billed against max_tokens.

    The task is extraction, not deliberation: read fourteen rules, quote the
    brief, answer. A model that reasons at length about it can spend the whole
    ceiling before writing a character of JSON — which is exactly how
    production returned nothing on a brief develop had just scored in 28s.
    Unset the setting to send no reasoning field and take the provider default.
    """
    effort = settings().llm_reasoning_effort.strip()
    return {"reasoning": {"effort": effort}} if effort else {}


async def _get_openrouter_client():
    """Reuse one connection pool without ever storing a caller's API key."""
    import httpx

    global _openrouter_client, _openrouter_client_factory, _openrouter_client_timeout
    timeout = settings().llm_timeout_seconds
    factory = httpx.AsyncClient
    if (
        _openrouter_client is None
        or _openrouter_client_factory is not factory
        or _openrouter_client_timeout != timeout
    ):
        if _openrouter_client is not None:
            await _openrouter_client.aclose()
        _openrouter_client = factory(timeout=timeout)
        _openrouter_client_factory = factory
        _openrouter_client_timeout = timeout
    return _openrouter_client


async def close_openrouter_client() -> None:
    """Close the shared pool during application shutdown."""
    global _openrouter_client, _openrouter_client_factory, _openrouter_client_timeout
    if _openrouter_client is not None:
        await _openrouter_client.aclose()
    _openrouter_client = None
    _openrouter_client_factory = None
    _openrouter_client_timeout = None


def _vendor(slug: str) -> str:
    return slug.split("/", 1)[0]


def resolve_verifier_model(judge_model: str) -> str:
    """The model that reviews suggestions (the verifier of the verifier).

    Explicit PB_VERIFIER_MODEL wins; "auto" prefers a different vendor from the
    allowlist, then a different same-vendor model, then the judge itself.
    Never raises.
    """
    cfg = settings()
    if cfg.verifier_model and cfg.verifier_model != "auto":
        return cfg.verifier_model
    allowed = available_models()
    for m in allowed:
        if _vendor(m) != _vendor(judge_model):
            return m
    for m in allowed:
        if m != judge_model:
            return m
    return judge_model


def resolve_suggest_model(requested: str | None, allow_any: bool = False) -> str:
    """Resolve suggestion generation separately from authoritative judging."""
    return resolve_model(requested or settings().suggest_model or None, allow_any=allow_any)


def resolve_model(requested: str | None, allow_any: bool = False) -> str:
    """Validate a per-request model against the server's allowlist.

    allow_any=True denotes a bring-your-own-key request. It accepts any valid
    slug unless the operator sets PB_BYOK_MODELS; welance tiers use that
    defense-in-depth allowlist for server-held keys forwarded by p007-16.
    """
    if not requested:
        return default_model()
    # OpenRouter model identifiers are vendor/name-like slugs. Reject control
    # characters and URL-ish payloads before they reach logs or an upstream.
    if len(requested) > 200 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", requested):
        raise ModelNotAllowed("model is not a valid provider slug")
    if allow_any:
        byok_allowed = [m.strip() for m in settings().byok_models.split(",") if m.strip()]
        if byok_allowed and requested not in byok_allowed:
            raise ModelNotAllowed(
                f"model '{requested}' is not enabled for BYOK on this server; choose one of: "
                + ", ".join(byok_allowed)
            )
        return requested
    allowed = available_models()
    if requested not in allowed:
        raise ModelNotAllowed(
            f"model '{requested}' is not enabled on this server; choose one of: {', '.join(allowed)}"
        )
    return requested


@lru_cache(maxsize=1)
def _anthropic():
    cfg = settings()
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise LLMNotConfigured("the 'anthropic' package is not installed.") from exc
    return anthropic.AsyncAnthropic(api_key=cfg.anthropic_api_key, timeout=cfg.llm_timeout_seconds)


async def complete(
    prompt: str,
    model: str | None = None,
    api_key: str | None = None,
    *,
    max_tokens: int | None = None,
    purpose: str = "judge",
) -> str:
    """api_key: an optional caller-supplied OpenRouter key (bring your own key).

    Used for this call only — never logged, never stored.
    """
    cfg = settings()
    use = resolve_model(model, allow_any=bool(api_key))
    ceiling = max_tokens or cfg.llm_max_tokens
    if api_key or _use_openrouter():
        started = time.monotonic()
        client = await _get_openrouter_client()
        resp = await client.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {api_key or cfg.openrouter_api_key}"},
            json={
                "model": use,
                "max_tokens": ceiling,
                **(
                    {"provider": {"sort": cfg.suggest_provider_sort}}
                    if purpose.startswith("suggest") and cfg.suggest_provider_sort
                    else {}
                ),
                **_sampling_kwargs(use),
                **_reasoning_kwargs(),
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        log.info(
            "llm purpose=%s provider=openrouter model=%s status=%s finish_reason=%s duration_ms=%d",
            purpose,
            use,
            resp.status_code,
            choice.get("finish_reason"),
            round((time.monotonic() - started) * 1000),
        )
        if choice.get("finish_reason") == "length":
            raise JudgeTruncated(f"the model stopped at the {ceiling}-token ceiling")
        return choice["message"]["content"] or ""
    if not cfg.anthropic_api_key:
        raise LLMNotConfigured(
            "set PB_OPENROUTER_API_KEY or PB_ANTHROPIC_API_KEY; the LLM judge is unavailable."
        )
    started = time.monotonic()
    msg = await _anthropic().messages.create(
        model=use,
        max_tokens=ceiling,
        **_sampling_kwargs(use),
        messages=[{"role": "user", "content": prompt}],
    )
    log.info(
        "llm purpose=%s provider=anthropic model=%s stop_reason=%s duration_ms=%d",
        purpose,
        use,
        getattr(msg, "stop_reason", None),
        round((time.monotonic() - started) * 1000),
    )
    if getattr(msg, "stop_reason", None) == "max_tokens":
        raise JudgeTruncated(f"the model stopped at the {ceiling}-token ceiling")
    return "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")
