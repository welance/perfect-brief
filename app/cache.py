"""Redis: verdict cache (deterministic LLM output at temp 0) + rate limiting.

Both degrade gracefully: if Redis is unavailable the service still scores, it
just doesn't cache or rate-limit. Redis is the only stateful dependency, and it
holds nothing but ephemeral cache — the service itself is stateless.
"""

from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from .settings import settings

log = logging.getLogger("perfect_brief.cache")

_redis: aioredis.Redis | None = None


async def connect() -> None:
    global _redis
    try:
        _redis = aioredis.from_url(settings().redis_url, decode_responses=True)
        await _redis.ping()
        log.info("redis connected: %s", settings().redis_url)
    except Exception as exc:  # noqa: BLE001
        log.warning("redis unavailable (%s) — running without cache/rate-limit", exc)
        _redis = None


async def close() -> None:
    if _redis is not None:
        await _redis.aclose()


async def get_json(key: str):
    if _redis is None:
        return None
    try:
        raw = await _redis.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:  # noqa: BLE001
        log.warning("cache get failed: %s", exc)
        return None


async def set_json(key: str, value, ttl: int) -> None:
    if _redis is None:
        return
    try:
        await _redis.set(key, json.dumps(value), ex=ttl)
    except Exception as exc:  # noqa: BLE001
        log.warning("cache set failed: %s", exc)


async def allow(bucket: str) -> bool:
    """Fixed-window rate limit. True = allowed. Fails open if Redis is down."""
    limit = settings().rate_limit_per_minute
    if limit <= 0 or _redis is None:
        return True
    try:
        key = f"rl:{bucket}"
        n = await _redis.incr(key)
        if n == 1:
            await _redis.expire(key, 60)
        return n <= limit
    except Exception as exc:  # noqa: BLE001
        log.warning("rate-limit check failed: %s", exc)
        return True
