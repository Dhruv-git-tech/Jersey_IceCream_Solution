# =============================================================================
# Jersey Ice Cream Platform — Database Engine & Session Management
# =============================================================================
# Async SQLAlchemy 2.0 engine with connection pooling, health checks,
# and session lifecycle management.
#
# Design Decision:
#   Using async SQLAlchemy for non-blocking database access. FastAPI's async
#   nature means blocking DB calls would waste worker threads. asyncpg is the
#   fastest PostgreSQL driver for Python.
#
# Connection Pool Sizing:
#   pool_size=20, max_overflow=10 → max 30 connections per worker.
#   With 4 workers → max 120 connections. PostgreSQL default max_connections=100,
#   so set PostgreSQL max_connections=200 in production.
#
# Failure Modes:
#   - Connection pool exhaustion: Requests get 503, pool_timeout controls wait
#   - Database restart: pool_recycle=1800 ensures stale connections are dropped
#   - Network partition: socket timeout + retry logic in repositories
# =============================================================================

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.config import get_settings

settings = get_settings()

# ─── Async Engine ────────────────────────────────────────────────────────────

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,  # Verify connections before checkout (prevents stale conn errors)
    echo=settings.db_echo,
    # Performance: Use orjson for JSON serialization in async driver
    connect_args={
        "server_settings": {
            "application_name": "jersey-backend",
            "jit": "off",  # Disable JIT for short-lived connections
        },
        "command_timeout": 30,  # Query timeout in seconds
    },
)

# ─── Session Factory ────────────────────────────────────────────────────────

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading after commit (common footgun)
    autoflush=False,  # Explicit flush control
    autocommit=False,
)


# ─── Session Dependency ─────────────────────────────────────────────────────


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional database session via FastAPI dependency injection.

    Session lifecycle:
        1. Session created from pool
        2. Yielded to request handler
        3. Committed if no exception
        4. Rolled back on exception
        5. Session closed and connection returned to pool

    Usage in FastAPI:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager version for use outside of FastAPI dependency injection.
    Used in background workers, CLI scripts, etc.
    """
    session = async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ─── Health Check ────────────────────────────────────────────────────────────


async def check_db_health() -> dict:
    """
    Verify database connectivity and return pool statistics.

    Returns:
        dict with status, pool_size, checked_out, overflow, and latency_ms
    """
    import time

    start = time.monotonic()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        pool = engine.pool
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# ─── Engine Lifecycle ────────────────────────────────────────────────────────


async def init_db() -> None:
    """Initialize database engine. Called at application startup."""
    # Verify connectivity
    health = await check_db_health()
    if health["status"] != "healthy":
        raise RuntimeError(f"Database health check failed: {health}")


async def close_db() -> None:
    """Dispose of database engine. Called at application shutdown."""
    await engine.dispose()
