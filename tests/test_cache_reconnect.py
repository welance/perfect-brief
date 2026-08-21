"""Redis startup failure degrades safely, then recovers without a pod restart."""

import asyncio

from app import cache


class FakeRedis:
    def __init__(self, *, ping_error=False):
        self.ping_error = ping_error
        self.closed = False

    async def ping(self):
        if self.ping_error:
            raise ConnectionError("sidecar is still starting")

    async def get(self, key):
        return '{"ready": true}'

    async def aclose(self):
        self.closed = True


def test_cache_recovers_after_initial_sidecar_race(monkeypatch):
    clients = [FakeRedis(ping_error=True), FakeRedis()]
    monkeypatch.setattr(cache.aioredis, "from_url", lambda *args, **kwargs: clients.pop(0))
    monkeypatch.setattr(cache, "_redis", None)
    monkeypatch.setattr(cache, "_connect_lock", None)
    monkeypatch.setattr(cache, "_retry_after", 0.0)

    assert asyncio.run(cache.get_json("first")) is None
    assert cache.connected() is False

    # Simulate the bounded retry interval elapsing; the next normal cache
    # operation reconnects, so no application restart is required.
    monkeypatch.setattr(cache, "_retry_after", 0.0)
    assert asyncio.run(cache.get_json("second")) == {"ready": True}
    assert cache.connected() is True

    asyncio.run(cache.close())
