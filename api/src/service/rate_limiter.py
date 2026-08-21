import asyncio
import time


class RateLimitExceeded(Exception):
    """Raised when a key has exceeded its request budget for the current window."""

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded, retry after {retry_after_seconds}s")


class RateLimiter:
    """Fixed-window request counter, keyed by an arbitrary string (typically a
    client IP). In-memory by default; if redis_url is set, uses Redis so counts
    are shared and correct across multiple serverless instances."""

    def __init__(self, redis_url: str | None, limit: int, window_seconds: int = 3600):
        self._redis_url = redis_url
        self._redis = None
        self._limit = limit
        self._window_seconds = window_seconds
        self._store: dict[str, tuple[int, int]] = {}
        self._lock = asyncio.Lock()

    async def _get_redis(self):
        if self._redis is None and self._redis_url:
            import redis.asyncio as aioredis

            self._redis = aioredis.from_url(self._redis_url)
        return self._redis

    async def check(self, key: str) -> None:
        """Increment the counter for `key`. Raises RateLimitExceeded if the
        request budget for the current window has already been used up."""
        now = time.time()
        window_start = int(now // self._window_seconds) * self._window_seconds
        retry_after = window_start + self._window_seconds - int(now)

        redis = await self._get_redis()
        if redis:
            redis_key = f"ratelimit:{key}:{window_start}"
            count = await redis.incr(redis_key)
            if count == 1:
                await redis.expire(redis_key, self._window_seconds)
            if count > self._limit:
                raise RateLimitExceeded(retry_after)
            return

        async with self._lock:
            stored_window, count = self._store.get(key, (window_start, 0))
            if stored_window != window_start:
                count = 0
            count += 1
            self._store[key] = (window_start, count)

        if count > self._limit:
            raise RateLimitExceeded(retry_after)
