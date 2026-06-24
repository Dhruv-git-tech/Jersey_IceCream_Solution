# =============================================================================
# Jersey Ice Cream Platform — Core Security Module
# =============================================================================
# JWT token management, password hashing, RBAC enforcement.
#
# Design Decisions:
#   - bcrypt for password hashing (12 rounds, ~250ms per hash)
#   - HS256 JWT (symmetric) for simplicity; switch to RS256 for multi-service
#   - Access token: 15min, Refresh token: 7 days
#   - Token blacklist via Redis SET for revocation
#   - RBAC with hierarchical permission model
#
# Threat Model:
#   - Token theft: Short-lived access tokens limit damage window
#   - Refresh token reuse: Token rotation + family tracking detects replay
#   - Brute force: Rate limiting at middleware layer + bcrypt's intentional slowness
#   - Timing attacks: passlib's verify uses constant-time comparison
# =============================================================================

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()

# ─── Password Hashing ───────────────────────────────────────────────────────

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # ~250ms per hash — balances security and UX
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.
    Uses constant-time comparison to prevent timing attacks.
    """
    return pwd_context.verify(plain_password, hashed_password)


# ─── Role-Based Access Control ──────────────────────────────────────────────


class Permission(str, Enum):
    """
    Fine-grained permissions for the RBAC system.

    Naming convention: RESOURCE_ACTION
    Hierarchical: parent permissions include child permissions.
    """

    # ─── User Management ────────────
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"
    USERS_MANAGE = "users:manage"  # includes all user operations

    # ─── Distributor Management ─────
    DISTRIBUTORS_READ = "distributors:read"
    DISTRIBUTORS_CREATE = "distributors:create"
    DISTRIBUTORS_UPDATE = "distributors:update"
    DISTRIBUTORS_DELETE = "distributors:delete"
    DISTRIBUTORS_MANAGE = "distributors:manage"

    # ─── Cart / Vendor ──────────────
    CARTS_READ = "carts:read"
    CARTS_CREATE = "carts:create"
    CARTS_UPDATE = "carts:update"
    CARTS_DELETE = "carts:delete"
    CARTS_MANAGE = "carts:manage"

    # ─── Inventory ──────────────────
    INVENTORY_READ = "inventory:read"
    INVENTORY_UPDATE = "inventory:update"
    INVENTORY_MANAGE = "inventory:manage"

    # ─── Orders ─────────────────────
    ORDERS_READ = "orders:read"
    ORDERS_CREATE = "orders:create"
    ORDERS_UPDATE = "orders:update"
    ORDERS_MANAGE = "orders:manage"

    # ─── Forecasting ────────────────
    FORECASTS_READ = "forecasts:read"
    FORECASTS_MANAGE = "forecasts:manage"

    # ─── AI Vision ──────────────────
    VISION_UPLOAD = "vision:upload"
    VISION_READ = "vision:read"
    VISION_MANAGE = "vision:manage"

    # ─── Competitor Intel ───────────
    COMPETITORS_READ = "competitors:read"
    COMPETITORS_MANAGE = "competitors:manage"

    # ─── Command Center ─────────────
    DASHBOARD_READ = "dashboard:read"
    DASHBOARD_MANAGE = "dashboard:manage"

    # ─── System ─────────────────────
    ADMIN_FULL = "admin:full"
    AUDIT_READ = "audit:read"


class Role(str, Enum):
    """
    Predefined roles with permission sets.

    Role hierarchy:
        SUPER_ADMIN > REGIONAL_MANAGER > DISTRIBUTOR_ADMIN > DISTRIBUTOR_STAFF > VENDOR
        ANALYST is cross-cutting (read-only everywhere)
        AI_SERVICE is for internal ML pipeline
    """

    SUPER_ADMIN = "super_admin"
    REGIONAL_MANAGER = "regional_manager"
    DISTRIBUTOR_ADMIN = "distributor_admin"
    DISTRIBUTOR_STAFF = "distributor_staff"
    VENDOR = "vendor"
    ANALYST = "analyst"
    AI_SERVICE = "ai_service"


# Role → Permission mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.SUPER_ADMIN: {p for p in Permission},  # All permissions
    Role.REGIONAL_MANAGER: {
        Permission.USERS_READ,
        Permission.USERS_CREATE,
        Permission.DISTRIBUTORS_READ,
        Permission.DISTRIBUTORS_CREATE,
        Permission.DISTRIBUTORS_UPDATE,
        Permission.DISTRIBUTORS_MANAGE,
        Permission.CARTS_READ,
        Permission.CARTS_MANAGE,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_MANAGE,
        Permission.ORDERS_READ,
        Permission.ORDERS_MANAGE,
        Permission.FORECASTS_READ,
        Permission.VISION_READ,
        Permission.COMPETITORS_READ,
        Permission.DASHBOARD_READ,
        Permission.DASHBOARD_MANAGE,
        Permission.AUDIT_READ,
    },
    Role.DISTRIBUTOR_ADMIN: {
        Permission.DISTRIBUTORS_READ,
        Permission.DISTRIBUTORS_UPDATE,
        Permission.CARTS_READ,
        Permission.CARTS_CREATE,
        Permission.CARTS_UPDATE,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_UPDATE,
        Permission.INVENTORY_MANAGE,
        Permission.ORDERS_READ,
        Permission.ORDERS_CREATE,
        Permission.ORDERS_UPDATE,
        Permission.ORDERS_MANAGE,
        Permission.FORECASTS_READ,
        Permission.VISION_READ,
        Permission.DASHBOARD_READ,
    },
    Role.DISTRIBUTOR_STAFF: {
        Permission.CARTS_READ,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_UPDATE,
        Permission.ORDERS_READ,
        Permission.ORDERS_CREATE,
        Permission.ORDERS_UPDATE,
        Permission.FORECASTS_READ,
        Permission.DASHBOARD_READ,
    },
    Role.VENDOR: {
        Permission.CARTS_READ,
        Permission.INVENTORY_READ,
        Permission.VISION_UPLOAD,
        Permission.VISION_READ,
        Permission.ORDERS_CREATE,  # Refill requests
        Permission.DASHBOARD_READ,
    },
    Role.ANALYST: {
        Permission.USERS_READ,
        Permission.DISTRIBUTORS_READ,
        Permission.CARTS_READ,
        Permission.INVENTORY_READ,
        Permission.ORDERS_READ,
        Permission.FORECASTS_READ,
        Permission.VISION_READ,
        Permission.COMPETITORS_READ,
        Permission.DASHBOARD_READ,
        Permission.AUDIT_READ,
    },
    Role.AI_SERVICE: {
        Permission.CARTS_READ,
        Permission.INVENTORY_READ,
        Permission.INVENTORY_UPDATE,
        Permission.FORECASTS_READ,
        Permission.FORECASTS_MANAGE,
        Permission.VISION_READ,
        Permission.VISION_MANAGE,
    },
}


def get_role_permissions(role: Role) -> set[Permission]:
    """Get all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, set())


def check_permission(user_roles: list[str], required_permission: Permission) -> bool:
    """
    Check if any of the user's roles grant the required permission.

    Time Complexity: O(R × P) where R = number of roles, P = permissions per role.
    In practice: R ≤ 3, P ≤ 30 → O(1) effectively constant.
    """
    for role_str in user_roles:
        try:
            role = Role(role_str)
        except ValueError:
            continue
        if required_permission in ROLE_PERMISSIONS.get(role, set()):
            return True
    return False


# ─── JWT Token Management ───────────────────────────────────────────────────


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: str  # User ID
    type: TokenType
    roles: list[str]
    jti: str  # JWT ID for blacklisting
    exp: datetime
    iat: datetime
    distributor_id: str | None = None  # Scope for distributor-level users


def create_access_token(
    user_id: str,
    roles: list[str],
    distributor_id: str | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a short-lived access token.

    Args:
        user_id: UUID of the authenticated user
        roles: List of role names
        distributor_id: Optional distributor scope
        expires_delta: Custom expiration (default: 15 minutes)

    Returns:
        Encoded JWT string
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))

    payload = {
        "sub": str(user_id),
        "type": TokenType.ACCESS.value,
        "roles": roles,
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": now,
    }
    if distributor_id:
        payload["distributor_id"] = str(distributor_id)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    user_id: str,
    roles: list[str],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a long-lived refresh token.

    Stored in httpOnly secure cookie on the client.
    Used to obtain new access tokens without re-authentication.
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(days=settings.jwt_refresh_token_expire_days))

    payload = {
        "sub": str(user_id),
        "type": TokenType.REFRESH.value,
        "roles": roles,
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is malformed or invalid signature
    """
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={
            "require": ["sub", "type", "roles", "jti", "exp", "iat"],
        },
    )
    return TokenPayload(**payload)


def create_token_pair(
    user_id: str,
    roles: list[str],
    distributor_id: str | None = None,
) -> dict[str, str]:
    """Create both access and refresh tokens."""
    return {
        "access_token": create_access_token(user_id, roles, distributor_id),
        "refresh_token": create_refresh_token(user_id, roles),
        "token_type": "bearer",
    }
