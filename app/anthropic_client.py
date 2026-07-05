"""Thin async wrapper around the Anthropic Messages API.

Lazily imported so the mock judge (and the whole test suite) runs with no SDK
and no API key. Temperature is pinned to 0 for reproducibility.
"""

from __future__ import annotations

from functools import lru_cache

from .settings import settings


class LLMNotConfigured(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _client():
    cfg = settings()
    if not cfg.anthropic_api_key:
        raise LLMNotConfigured("PB_ANTHROPIC_API_KEY is not set; the LLM judge is unavailable.")
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise LLMNotConfigured("the 'anthropic' package is not installed.") from exc
    return anthropic.AsyncAnthropic(api_key=cfg.anthropic_api_key)


def configured() -> bool:
    return bool(settings().anthropic_api_key)


async def complete(prompt: str) -> str:
    cfg = settings()
    msg = await _client().messages.create(
        model=cfg.model,
        max_tokens=cfg.llm_max_tokens,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if getattr(block, "type", None) == "text")
