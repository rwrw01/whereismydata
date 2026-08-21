import pytest

from src.service.rate_limiter import RateLimitExceeded, RateLimiter


async def test_allows_requests_up_to_the_limit():
    limiter = RateLimiter(redis_url=None, limit=3, window_seconds=3600)
    await limiter.check("1.2.3.4")
    await limiter.check("1.2.3.4")
    await limiter.check("1.2.3.4")


async def test_blocks_requests_over_the_limit():
    limiter = RateLimiter(redis_url=None, limit=2, window_seconds=3600)
    await limiter.check("1.2.3.4")
    await limiter.check("1.2.3.4")
    with pytest.raises(RateLimitExceeded):
        await limiter.check("1.2.3.4")


async def test_tracks_different_keys_independently():
    limiter = RateLimiter(redis_url=None, limit=1, window_seconds=3600)
    await limiter.check("1.2.3.4")
    await limiter.check("5.6.7.8")


async def test_retry_after_is_positive_and_within_window():
    limiter = RateLimiter(redis_url=None, limit=1, window_seconds=3600)
    await limiter.check("1.2.3.4")
    with pytest.raises(RateLimitExceeded) as exc_info:
        await limiter.check("1.2.3.4")
    assert 0 < exc_info.value.retry_after_seconds <= 3600


async def test_resets_after_the_window_expires(monkeypatch):
    import src.service.rate_limiter as rate_limiter_module

    current_time = [1_000_000.0]
    monkeypatch.setattr(rate_limiter_module.time, "time", lambda: current_time[0])

    limiter = RateLimiter(redis_url=None, limit=1, window_seconds=3600)
    await limiter.check("1.2.3.4")
    with pytest.raises(RateLimitExceeded):
        await limiter.check("1.2.3.4")

    current_time[0] += 3600
    await limiter.check("1.2.3.4")
