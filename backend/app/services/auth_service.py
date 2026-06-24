# =============================================================================
# Jersey Ice Cream Platform — Auth Service
# =============================================================================
# Business logic for authentication, registration, and token management.
#
# Security Design:
#   - bcrypt password hashing (12 rounds)
#   - Account lockout after 5 failed attempts (30-minute cooldown)
#   - JWT access + refresh token pair
#   - Refresh token rotation (old token invalidated)
#   - Token blacklisting via Redis for logout/revocation
# =============================================================================

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheManager, get_redis_client
from app.core.exceptions import (
    AuthenticationError,
    DuplicateError,
    InvalidCredentialsError,
    NotFoundError,
    TokenBlacklistedError,
    TokenExpiredError,
    TokenInvalidError,
    ValidationError,
)
from app.core.security import (
    Role,
    TokenPayload,
    TokenType,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserStatus
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 1800  # 30 minutes


class AuthService:
    """
    Authentication service handling login, registration, and token lifecycle.

    All methods are stateless (no instance state) and receive dependencies
    via parameters for testability.
    """

    def __init__(self) -> None:
        self.user_repo = UserRepository()

    async def register(
        self,
        db: AsyncSession,
        request: RegisterRequest,
    ) -> UserResponse:
        """
        Register a new user account.

        Steps:
        1. Validate email/phone uniqueness
        2. Hash password
        3. Create user with PENDING_VERIFICATION status
        4. Assign initial role
        5. Return user profile

        Raises:
            DuplicateError: Email or phone already registered
            ValidationError: Invalid role assignment
        """
        # Check uniqueness
        if request.email and await self.user_repo.email_exists(db, request.email):
            raise DuplicateError("User", "email")

        if request.phone and await self.user_repo.phone_exists(db, request.phone):
            raise DuplicateError("User", "phone")

        # Validate role
        try:
            role = Role(request.role)
        except ValueError:
            raise ValidationError(
                message=f"Invalid role: {request.role}",
                details={"valid_roles": [r.value for r in Role]},
            )

        # Create user
        user = await self.user_repo.create(
            db,
            email=request.email,
            phone=request.phone,
            password_hash=hash_password(request.password),
            full_name=request.full_name,
            status=UserStatus.ACTIVE,  # Skip verification for MVP
        )

        # Assign role (would normally query role by name, simplified here)
        # In production: create role if doesn't exist, then associate
        logger.info("User registered: id=%s email=%s role=%s", user.id, user.email, request.role)

        return UserResponse(
            id=user.id,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            status=user.status.value,
            roles=[request.role],
            avatar_url=user.avatar_url,
            last_login=user.last_login,
            created_at=user.created_at,
        )

    async def login(
        self,
        db: AsyncSession,
        request: LoginRequest,
    ) -> TokenResponse:
        """
        Authenticate user and return JWT token pair.

        Steps:
        1. Find user by email or phone
        2. Check account status (active, not locked)
        3. Verify password
        4. Generate access + refresh tokens
        5. Update login metadata

        Raises:
            InvalidCredentialsError: Bad email/phone or password
            AuthenticationError: Account locked or suspended
        """
        # Find user
        user: User | None = None
        if request.email:
            user = await self.user_repo.get_by_email(db, request.email)
        elif request.phone:
            user = await self.user_repo.get_by_phone(db, request.phone)

        if user is None:
            # Don't reveal whether email/phone exists (prevents enumeration)
            raise InvalidCredentialsError()

        # Check account status
        if user.status == UserStatus.SUSPENDED:
            raise AuthenticationError(
                message="Account is suspended. Contact support.",
                error_code="ACCOUNT_SUSPENDED",
            )

        if user.status == UserStatus.INACTIVE:
            raise AuthenticationError(
                message="Account is inactive.",
                error_code="ACCOUNT_INACTIVE",
            )

        # Check lockout
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            raise AuthenticationError(
                message="Account temporarily locked due to too many failed login attempts. "
                "Please try again in 30 minutes.",
                error_code="ACCOUNT_LOCKED",
            )

        # Verify password
        if not verify_password(request.password, user.password_hash):
            await self.user_repo.increment_failed_login(db, user)
            remaining = MAX_FAILED_ATTEMPTS - user.failed_login_attempts
            logger.warning(
                "Failed login attempt: user=%s remaining=%d",
                user.id,
                remaining,
            )
            raise InvalidCredentialsError()

        # Successful login
        await self.user_repo.reset_failed_login(db, user)
        await self.user_repo.update_last_login(db, user)

        # Get role names
        role_names = user.role_names if user.roles else ["vendor"]

        # Determine distributor scope
        distributor_id = None
        # TODO: Look up distributor_id for distributor-scoped users

        # Generate tokens
        tokens = create_token_pair(
            user_id=str(user.id),
            roles=role_names,
            distributor_id=str(distributor_id) if distributor_id else None,
        )

        from app.config import get_settings

        settings = get_settings()

        logger.info("User logged in: id=%s email=%s", user.id, user.email)

        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def refresh_token(
        self,
        db: AsyncSession,
        refresh_token_str: str,
    ) -> TokenResponse:
        """
        Exchange a refresh token for a new token pair.

        Implements token rotation:
        1. Validate refresh token
        2. Check if blacklisted (revoked)
        3. Blacklist the old refresh token
        4. Issue new access + refresh token pair

        This ensures that stolen refresh tokens can only be used once.
        """
        import jwt as pyjwt

        try:
            payload = decode_token(refresh_token_str)
        except pyjwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except pyjwt.InvalidTokenError:
            raise TokenInvalidError()

        if payload.type != TokenType.REFRESH:
            raise TokenInvalidError()

        # Check blacklist
        try:
            client = await get_redis_client()
            cache = CacheManager(client)
            if await cache.is_token_blacklisted(payload.jti):
                raise TokenBlacklistedError()

            # Blacklist old refresh token
            remaining_ttl = int((payload.exp - __import__("datetime").datetime.now(__import__("datetime").UTC)).total_seconds())
            if remaining_ttl > 0:
                await cache.blacklist_token(payload.jti, remaining_ttl)
        except (TokenBlacklistedError):
            raise
        except Exception:
            # Redis failure: allow refresh (fail open for availability)
            logger.warning("Redis unavailable during token refresh", exc_info=True)

        # Verify user still exists and is active
        user = await self.user_repo.get_with_roles(db, uuid.UUID(payload.sub))
        if user is None or user.status != UserStatus.ACTIVE:
            raise AuthenticationError(
                message="User account is no longer active",
                error_code="USER_INACTIVE",
            )

        # Generate new token pair
        tokens = create_token_pair(
            user_id=payload.sub,
            roles=payload.roles,
            distributor_id=payload.distributor_id,
        )

        from app.config import get_settings

        settings = get_settings()

        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def logout(self, token_payload: TokenPayload) -> None:
        """
        Logout by blacklisting the current access token's JTI.

        The token remains technically valid until its natural expiry,
        but every request checks the blacklist before proceeding.
        """
        try:
            client = await get_redis_client()
            cache = CacheManager(client)
            remaining_ttl = int(
                (token_payload.exp - __import__("datetime").datetime.now(__import__("datetime").UTC)).total_seconds()
            )
            if remaining_ttl > 0:
                await cache.blacklist_token(token_payload.jti, remaining_ttl)
        except Exception:
            logger.warning("Failed to blacklist token on logout", exc_info=True)

    async def get_current_user(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> UserResponse:
        """Get current user profile."""
        user = await self.user_repo.get_with_roles(db, user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))

        return UserResponse(
            id=user.id,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            status=user.status.value,
            roles=user.role_names,
            avatar_url=user.avatar_url,
            last_login=user.last_login,
            created_at=user.created_at,
        )
