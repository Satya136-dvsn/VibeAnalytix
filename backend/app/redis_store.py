"""
Redis connection pool management for the application.
Provides async Redis client with connection pooling.
"""

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

# Global Redis connection pool
_redis_pool: ConnectionPool | None = None


async def init_redis(redis_url: str) -> None:
    """
    Initialize the global Redis connection pool.
    
    Should be called once at application startup.
    
    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
    """
    global _redis_pool
    _redis_pool = ConnectionPool.from_url(redis_url, decode_responses=True)


async def get_redis() -> redis.Redis:
    """
    Get a Redis client from the connection pool.
    
    Must be called after init_redis() has been invoked.
    
    Returns:
        Redis client instance using the shared connection pool
        
    Raises:
        RuntimeError: If init_redis() has not been called
    """
    if _redis_pool is None:
        raise RuntimeError("Redis pool not initialized. Call init_redis() first.")
    return redis.Redis(connection_pool=_redis_pool)


async def close_redis() -> None:
    """
    Close the global Redis connection pool.
    
    Should be called at application shutdown.
    """
    global _redis_pool
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
