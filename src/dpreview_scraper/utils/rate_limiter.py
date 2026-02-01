"""Token bucket rate limiter."""

import asyncio
import random
import time
from typing import Optional


class RateLimiter:
    """Token bucket rate limiter with jitter."""

    def __init__(
        self,
        requests_per_minute: int = 20,
        jitter_min: float = 0.5,
        jitter_max: float = 2.0,
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            jitter_min: Minimum jitter delay in seconds
            jitter_max: Maximum jitter delay in seconds
        """
        self.requests_per_minute = requests_per_minute
        self.jitter_min = jitter_min
        self.jitter_max = jitter_max

        # Token bucket parameters
        self.tokens = float(requests_per_minute)
        self.max_tokens = float(requests_per_minute)
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.last_refill = time.time()

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.max_tokens, self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

    async def acquire(self, tokens: float = 1.0) -> None:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire
        """
        while True:
            self._refill_tokens()

            if self.tokens >= tokens:
                self.tokens -= tokens
                # Add jitter to make requests look more human-like
                jitter = random.uniform(self.jitter_min, self.jitter_max)
                await asyncio.sleep(jitter)
                return

            # Wait for tokens to refill
            wait_time = (tokens - self.tokens) / self.refill_rate
            await asyncio.sleep(wait_time)

    def available_tokens(self) -> float:
        """Get current number of available tokens."""
        self._refill_tokens()
        return self.tokens
