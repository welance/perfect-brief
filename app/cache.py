"""Redis: verdict cache (deterministic LLM output at temp 0) + rate limiting.

Both degrade gracefully: if Redis is unavailable the service still scores, it
just doesn't cache or rate-limit. Redis is the only stateful dependency, and it
holds nothing but ephemeral cache — the service itself is stateless.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

import redis.asyncio as aioredis

from .settings import settings

log = logging.getLogger("perfect_brief.cache")

_redis: aioredis.Redis | None = None
_connect_lock: asyncio.Lock | None = None
_retry_after = 0.0
_RECONNECT_SECONDS = 10.0


async def _client() -> aioredis.Redis | None:
    """Connect lazily so a sidecar starting after the API can still recover.

    Redis is optional, but one failed startup ping must not disable caching and
    rate limiting for the pod's entire lifetime. The short backoff prevents an
    unavailable dependency from adding work to every request.
    """
    global _redis, _connect_lock, _retry_after
    if _redis is not None:
        return _redis
    if time.monotonic() < _retry_after:
        return None
    if _connect_lock is None:
        _connect_lock = asyncio.Lock()
    async with _connect_lock:
        if _redis is not None:
            return _redis
        if time.monotonic() < _retry_after:
            return None
        candidate = aioredis.from_url(settings().redis_url, decode_responses=True)
        try:
            await candidate.ping()
        except Exception as exc:  # noqa: BLE001
            _retry_after = time.monotonic() + _RECONNECT_SECONDS
            await candidate.aclose()
            # Never log the URL itself: it may carry a password.
            log.warning("redis unavailable (%s) — running without cache/rate-limit", exc)
            return None
        _redis = candidate
        _retry_after = 0.0
        log.info("redis connected")
        return _redis


async def _failed(client: aioredis.Redis, operation: str, exc: Exception) -> None:
    global _redis, _retry_after
    if _redis is client:
        _redis = None
    _retry_after = time.monotonic() + _RECONNECT_SECONDS
    await client.aclose()
    log.warning("%s failed: %s", operation, exc)


async def connect() -> None:
    await _client()


async def close() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def connected() -> bool:
    return _redis is not None


async def get_json(key: str):
    client = await _client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:  # noqa: BLE001
        await _failed(client, "cache get", exc)
        return None


async def set_json(key: str, value, ttl: int) -> None:
    client = await _client()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(value), ex=ttl)
    except Exception as exc:  # noqa: BLE001
        await _failed(client, "cache set", exc)


async def allow(bucket: str, limit: int | None = None) -> bool:
    """Fixed-window rate limit. True = allowed. Fails open if Redis is down."""
    limit = settings().rate_limit_per_minute if limit is None else limit
    if limit <= 0:
        return True
    client = await _client()
    if client is None:
        return True
    try:
        key = f"rl:{bucket}"
        n = await client.incr(key)
        if n == 1:
            await client.expire(key, 60)
        return n <= limit
    except Exception as exc:  # noqa: BLE001
        await _failed(client, "rate-limit check", exc)
        return True
