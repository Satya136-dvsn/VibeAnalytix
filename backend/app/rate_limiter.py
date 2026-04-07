"""
Redis-backed sliding window rate limiter.

Implements atomic limits using Redis sorted sets:
- Remove expired events
- Count current window
- Add current event if under limit
"""

from __future__ import annotations

import time
from uuid import uuid4

from app.redis_store import get_redis


class RateLimitError(Exception):
    """Raised when a request exceeds the configured rate limit."""


_ATOMIC_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local ttl_seconds = tonumber(ARGV[5])

local window_start = now - window_ms
redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

local current = redis.call('ZCARD', key)
if current >= limit then
    return 0
end

redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, ttl_seconds)
return 1
"""


async def enforce_sliding_window_limit(
    *,
    key: str,
    limit: int,
    window_seconds: int,
) -> None:
    """
    Enforce a Redis sliding-window rate limit.

    Args:
        key: Redis key namespace for this limit bucket.
        limit: Maximum allowed requests in the window.
        window_seconds: Window size in seconds.

    Raises:
        RateLimitError: If the request exceeds the rate limit.
    """
    redis_client = await get_redis()

    now_ms = int(time.time() * 1000)
    window_ms = window_seconds * 1000
    member = f"{now_ms}:{uuid4()}"

    allowed = await redis_client.eval(
        _ATOMIC_SLIDING_WINDOW_SCRIPT,
        1,
        key,
        now_ms,
        window_ms,
        limit,
        member,
        window_seconds,
    )

    if int(allowed) != 1:
        raise RateLimitError(
            f"Rate limit exceeded: max {limit} requests in {window_seconds} seconds"
        )
