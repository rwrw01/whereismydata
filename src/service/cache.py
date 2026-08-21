import time


class TTLCache:
    """TTL cache. In-memory dict by default; if redis_url is set, uses
    Redis instead so cached values survive across process restarts /
    are shared across serverless instances."""

    def __init__(self, redis_url: str | None = None, ttl_seconds: int = 604800):
        self._ttl_seconds = ttl_seconds
        self._redis_url = redis_url
        self._redis = None
        self._store: dict[str, tuple[float, str]] = {}

    async def _get_redis(self):
        if self._redis is None and self._redis_url:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url)
        return self._redis

    async def get(self, key: str) -> str | None:
        redis = await self._get_redis()
        if redis:
            value = await redis.get(key)
            return value.decode() if value is not None else None

        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: str) -> None:
        redis = await self._get_redis()
        if redis:
            await redis.setex(key, self._ttl_seconds, value)
            return
        self._store[key] = (time.monotonic() + self._ttl_seconds, value)
