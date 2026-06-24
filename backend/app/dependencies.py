# =============================================================================
# Jersey Ice Cream Platform — Dependencies (FastAPI Dependency Injection)
# =============================================================================

from __future__ import annotations

import uuid
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.cache import CacheManager, get_redis_client
from app.core.exceptions import (
    InsufficientPermissionsError,
    TokenBlacklistedError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.core.security import (
    Permission,
    TokenPayload,
    TokenType,
    check_permission,
    decode_token,
)
from app.database import get_db_session

settings = get_settings()


# ─── Database Session ────────────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


# ─── Authentication ─────────────────────────────────────────────────────────


async def get_current_token(
    authorization: str = Header(None, alias="Authorization"),
) -> TokenPayload:
    """
    Extract and validate JWT from Authorization header.

    Expected format: Bearer <token>

    Checks:
    1. Header present and well-formed
    2. Token signature valid
    3. Token not expired
    4. Token not blacklisted in Redis
    """
    if not authorization:
        raise TokenInvalidError()

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise TokenInvalidError()

    token = parts[1]

    try:
        payload = decode_token(token)
    except pyjwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except pyjwt.InvalidTokenError:
        raise TokenInvalidError()

    if payload.type != TokenType.ACCESS:
        raise TokenInvalidError()

    # Check blacklist
    try:
        client = await get_redis_client()
        cache = CacheManager(client)
        if await cache.is_token_blacklisted(payload.jti):
            raise TokenBlacklistedError()
    except TokenBlacklistedError:
        raise
    except Exception:
        # Redis failure: allow access (fail open)
        pass

    return payload


CurrentToken = Annotated[TokenPayload, Depends(get_current_token)]


async def get_current_user_id(token: CurrentToken) -> uuid.UUID:
    """Extract user ID from validated token."""
    return uuid.UUID(token.sub)


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]


# ─── Permission Checking ────────────────────────────────────────────────────


def require_permission(permission: Permission):
    """
    FastAPI dependency that checks if the current user has a specific permission.

    Usage:
        @router.get("/distributors")
        async def list_distributors(
            _: None = Depends(require_permission(Permission.DISTRIBUTORS_READ)),
        ):
            ...
    """

    async def _check(token: CurrentToken) -> None:
        if not check_permission(token.roles, permission):
            raise InsufficientPermissionsError(required_permission=permission.value)

    return _check


def require_any_permission(*permissions: Permission):
    """Check if user has ANY of the listed permissions."""

    async def _check(token: CurrentToken) -> None:
        for perm in permissions:
            if check_permission(token.roles, perm):
                return
        raise InsufficientPermissionsError(
            required_permission=", ".join(p.value for p in permissions),
        )

    return _check


# ─── Distributor Scope ───────────────────────────────────────────────────────


async def get_distributor_scope(token: CurrentToken) -> uuid.UUID | None:
    """
    Get the distributor ID scope from the token.

    Used to enforce row-level security: distributor users can only
    access their own distributor's data.
    """
    if token.distributor_id:
        return uuid.UUID(token.distributor_id)
    return None


DistributorScope = Annotated[uuid.UUID | None, Depends(get_distributor_scope)]
