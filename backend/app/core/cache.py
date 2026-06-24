# =============================================================================
# Jersey Ice Cream Platform — Redis Cache Wrapper
# =============================================================================
# Async Redis client with connection pooling, health checks, and typed
# operations for caching, rate limiting, and token blacklisting.
#
# Design Decision:
#   Using redis-py's async interface with hiredis parser for performance.
#   hiredis is a C-based parser that's ~10x faster than the pure Python parser.
#
# Data Structure Usage:
#   - STRING: Simple key-value cache (KPI values, session data)
#   - SET: Token blacklist (O(1) lookup for revoked JTIs)
#   - SORTED SET: Rate limiting (sliding window counter)
#   - HASH: Complex cached objects (cart state, forecast results)
#   - LIST: Recent events buffer
#
# Failure Mode:
#   Redis is a cache, not source of truth. If Redis is down:
#   - Cache misses fall through to PostgreSQL (slower but correct)
#   - Rate limiting degrades gracefully (allow requests)
#   - Token blacklist degrades (tokens valid until natural expiry)
# =============================================================================

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Connection Pool ────────────────────────────────────────────────────────

_pool: ConnectionPool | None = None
_client: Redis | None = None


async def get_redis_pool() -> ConnectionPool:
    """Get or create the Redis connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            socket_timeout=settings.redis_socket_timeout,
            retry_on_timeout=settings.redis_retry_on_timeout,
            decode_responses=True,
            health_check_interval=30,
        )
    return _pool


async def get_redis_client() -> Redis:
    """Get or create the Redis client."""
    global _client
    if _client is None:
        pool = await get_redis_pool()
        _client = Redis(connection_pool=pool)
    return _client


async def close_redis() -> None:
    """Close Redis connection pool. Called at application shutdown."""
    global _client, _pool
    if _client:
        await _client.aclose()
        _client = None
    if _pool:
        await _pool.disconnect()
        _pool = None


# ─── Cache Operations ───────────────────────────────────────────────────────


class CacheManager:
    """
    High-level cache operations with namespaced keys and serialization.

    Key Naming Convention:
        jersey:{namespace}:{key}
        Example: jersey:kpi:revenue_daily, jersey:cart:abc123:inventory
    """

    PREFIX = "jersey"

    def __init__(self, client: Redis) -> None:
        self._client = client

    def _key(self, namespace: str, key: str) -> str:
        """Build a namespaced cache key."""
        return f"{self.PREFIX}:{namespace}:{key}"

    # ─── Basic Operations ───────────────────────────────────────────────

    async def get(self, namespace: str, key: str) -> str | None:
        """Get a cached value. Returns None on miss."""
        try:
            return await self._client.get(self._key(namespace, key))
        except redis.RedisError:
            logger.warning("Redis GET failed for %s:%s", namespace, key, exc_info=True)
            return None

    async def get_json(self, namespace: str, key: str) -> dict | list | None:
        """Get a cached JSON value, deserialized."""
        raw = await self.get(namespace, key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in cache for %s:%s", namespace, key)
            return None

    async def set(
        self,
        namespace: str,
        key: str,
        value: str | dict | list,
        ttl_seconds: int = 300,
    ) -> bool:
        """
        Set a cached value with TTL.

        Args:
            namespace: Cache namespace (e.g., 'kpi', 'cart', 'forecast')
            key: Cache key within namespace
            value: String or JSON-serializable value
            ttl_seconds: Time-to-live in seconds (default: 5 minutes)

        Returns:
            True if successful, False on error
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            await self._client.set(
                self._key(namespace, key),
                value,
                ex=ttl_seconds,
            )
            return True
        except redis.RedisError:
            logger.warning("Redis SET failed for %s:%s", namespace, key, exc_info=True)
            return False

    async def delete(self, namespace: str, key: str) -> bool:
        """Delete a cached value."""
        try:
            await self._client.delete(self._key(namespace, key))
            return True
        except redis.RedisError:
            logger.warning("Redis DELETE failed for %s:%s", namespace, key, exc_info=True)
            return False

    async def delete_pattern(self, namespace: str, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        WARNING: Uses SCAN, not KEYS. Safe for production.
        """
        full_pattern = self._key(namespace, pattern)
        deleted = 0
        try:
            async for key in self._client.scan_iter(match=full_pattern, count=100):
                await self._client.delete(key)
                deleted += 1
        except redis.RedisError:
            logger.warning("Redis pattern delete failed for %s", full_pattern, exc_info=True)
        return deleted

    # ─── Token Blacklist ────────────────────────────────────────────────

    async def blacklist_token(self, jti: str, ttl_seconds: int) -> bool:
        """
        Add a JWT ID to the blacklist.

        Uses SET data structure for O(1) lookup.
        TTL matches the token's remaining lifetime.
        """
        try:
            await self._client.set(
                self._key("blacklist", jti),
                "1",
                ex=ttl_seconds,
            )
            return True
        except redis.RedisError:
            logger.warning("Failed to blacklist token %s", jti, exc_info=True)
            return False

    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if a JWT ID is blacklisted. O(1) lookup."""
        try:
            return await self._client.exists(self._key("blacklist", jti)) > 0
        except redis.RedisError:
            # Fail open: if Redis is down, allow the token
            # This is a tradeoff: availability > security for short periods
            logger.warning("Redis blacklist check failed for %s", jti, exc_info=True)
            return False

    # ─── Rate Limiting (Sliding Window) ─────────────────────────────────

    async def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """
        Sliding window rate limiter using sorted sets.

        Algorithm:
            1. Remove expired entries (older than window)
            2. Count remaining entries
            3. If under limit, add new entry
            4. Return (is_allowed, remaining_requests)

        Time Complexity: O(log N) per check where N = entries in window
        Space Complexity: O(N) per key

        Args:
            identifier: Rate limit key (e.g., user_id, IP address)
            max_requests: Maximum requests allowed in window
            window_seconds: Window size in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        import time

        key = self._key("ratelimit", identifier)
        now = time.time()
        window_start = now - window_seconds

        try:
            pipe = self._client.pipeline(transaction=True)
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current entries
            pipe.zcard(key)
            # Add new entry
            pipe.zadd(key, {str(now): now})
            # Set TTL on the key
            pipe.expire(key, window_seconds)
            results = await pipe.execute()

            current_count = results[1]
            remaining = max(0, max_requests - current_count)
            is_allowed = current_count < max_requests

            if not is_allowed:
                # Remove the entry we just added since request is denied
                await self._client.zrem(key, str(now))

            return is_allowed, remaining
        except redis.RedisError:
            # Fail open: allow requests if Redis is down
            logger.warning("Rate limit check failed for %s", identifier, exc_info=True)
            return True, max_requests

    # ─── Pub/Sub for Real-time Updates ──────────────────────────────────

    async def publish(self, channel: str, message: dict) -> int:
        """
        Publish a message to a Redis channel for real-time dashboard updates.

        Returns number of subscribers that received the message.
        """
        try:
            return await self._client.publish(
                f"{self.PREFIX}:{channel}",
                json.dumps(message, default=str),
            )
        except redis.RedisError:
            logger.warning("Redis publish failed for channel %s", channel, exc_info=True)
            return 0


# ─── Health Check ────────────────────────────────────────────────────────────


async def check_redis_health() -> dict:
    """Verify Redis connectivity and return server info."""
    import time

    start = time.monotonic()
    try:
        client = await get_redis_client()
        await client.ping()
        info = await client.info("memory")
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", "unknown"),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
