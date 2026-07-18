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

from functools import lru_cache

from .settings import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class LLMNotConfigured(RuntimeError):
    pass


class ModelNotAllowed(LookupError):
    pass


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


def resolve_model(requested: str | None, allow_any: bool = False) -> str:
    """Validate a per-request model against the server's allowlist.

    allow_any=True (bring-your-own-key requests): the caller pays, so any
    model is accepted — it is still recorded in the cache key and response.
    """
    if not requested:
        return default_model()
    if allow_any:
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
    return anthropic.AsyncAnthropic(api_key=cfg.anthropic_api_key)


async def complete(prompt: str, model: str | None = None, api_key: str | None = None) -> str:
    """api_key: an optional caller-supplied OpenRouter key (bring your own key).

    Used for this call only — never logged, never stored.
    """
    cfg = settings()
    use = resolve_model(model, allow_any=bool(api_key))
    if api_key or _use_openrouter():
        import httpx

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {api_key or cfg.openrouter_api_key}"},
                json={
                    "model": use,
                    "max_tokens": cfg.llm_max_tokens,
                    **_sampling_kwargs(use),
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"] or ""
    if not cfg.anthropic_api_key:
        raise LLMNotConfigured(
            "set PB_OPENROUTER_API_KEY or PB_ANTHROPIC_API_KEY; the LLM judge is unavailable."
        )
    msg = await _anthropic().messages.create(
        model=use,
        max_tokens=cfg.llm_max_tokens,
        **_sampling_kwargs(use),
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")
