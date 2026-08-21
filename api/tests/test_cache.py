from src.service.cache import TTLCache


async def test_in_memory_cache_roundtrip():
    cache = TTLCache(redis_url=None, ttl_seconds=604800)
    assert await cache.get("missing") is None

    await cache.set("key", "value")
    assert await cache.get("key") == "value"


async def test_in_memory_cache_expires(monkeypatch):
    import src.service.cache as cache_module

    fake_time = [1000.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: fake_time[0])

    cache = TTLCache(redis_url=None, ttl_seconds=10)
    await cache.set("key", "value")
    assert await cache.get("key") == "value"

    fake_time[0] = 1011.0  # 11s later, past the 10s TTL
    assert await cache.get("key") is None
