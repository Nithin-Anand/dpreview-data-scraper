"""Tests for rate limiter."""

import asyncio
import time

import pytest

from dpreview_scraper.utils.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_initialization(self):
        limiter = RateLimiter(requests_per_minute=30, jitter_min=0, jitter_max=0)
        assert limiter.requests_per_minute == 30
        assert limiter.max_tokens == 30.0
        assert limiter.tokens == 30.0

    def test_available_tokens(self):
        limiter = RateLimiter(requests_per_minute=30, jitter_min=0, jitter_max=0)
        assert limiter.available_tokens() == 30.0

    @pytest.mark.asyncio
    async def test_acquire_consumes_token(self):
        limiter = RateLimiter(requests_per_minute=60, jitter_min=0, jitter_max=0)
        initial = limiter.available_tokens()
        await limiter.acquire()
        # Token should be consumed (allowing for small refill during async sleep)
        assert limiter.tokens < initial

    @pytest.mark.asyncio
    async def test_acquire_with_jitter_adds_delay(self):
        limiter = RateLimiter(
            requests_per_minute=60,
            jitter_min=0.05,
            jitter_max=0.1,
        )
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start
        assert elapsed >= 0.05

    def test_refill_over_time(self):
        limiter = RateLimiter(requests_per_minute=60, jitter_min=0, jitter_max=0)
        limiter.tokens = 0.0
        # Simulate time passing
        limiter.last_refill = time.time() - 1.0  # 1 second ago
        tokens = limiter.available_tokens()
        # Should refill ~1 token per second at 60 rpm
        assert tokens >= 0.9

    def test_tokens_capped_at_max(self):
        limiter = RateLimiter(requests_per_minute=10, jitter_min=0, jitter_max=0)
        limiter.last_refill = time.time() - 600  # 10 minutes ago
        tokens = limiter.available_tokens()
        assert tokens == 10.0
