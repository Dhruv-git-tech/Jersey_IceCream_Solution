# =============================================================================
# Jersey Ice Cream Platform — Auth API Routes
# =============================================================================

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.dependencies import CurrentToken, CurrentUserId
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register a new user",
    description="Create a new user account with email/phone and password.",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Register a new user account."""
    return await auth_service.register(db, request)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login",
    description="Authenticate with email/phone and password. Returns JWT token pair.",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate user and return access + refresh token pair."""
    return await auth_service.login(db, request)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new token pair.",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Get new token pair using refresh token."""
    return await auth_service.refresh_token(db, request.refresh_token)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout",
    description="Invalidate the current access token.",
)
async def logout(
    token: CurrentToken,
) -> MessageResponse:
    """Logout by blacklisting the current token."""
    await auth_service.logout(token)
    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get the profile of the currently authenticated user.",
)
async def get_me(
    user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Get current user profile."""
    return await auth_service.get_current_user(db, user_id)
