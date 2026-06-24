# =============================================================================
# Jersey Ice Cream Platform — Auth Schemas
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """Login with email/phone and password."""

    email: str | None = None
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", "phone")
    @classmethod
    def at_least_one_identifier(cls, v: str | None, info: object) -> str | None:
        return v

    def model_post_init(self, __context: object) -> None:
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided")


class TokenResponse(BaseModel):
    """JWT token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token expiry in seconds")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class RegisterRequest(BaseModel):
    """New user registration."""

    email: str | None = None
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    role: str = Field(default="vendor", description="Initial role assignment")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Enforce password complexity."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    def model_post_init(self, __context: object) -> None:
        if not self.email and not self.phone:
            raise ValueError("Either email or phone must be provided")


class PasswordChangeRequest(BaseModel):
    """Change password for authenticated user."""

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    """User profile response."""

    id: uuid.UUID
    email: str | None
    phone: str | None
    full_name: str
    status: str
    roles: list[str]
    avatar_url: str | None
    last_login: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSummary(BaseModel):
    """Compact user reference for embedding in other responses."""

    id: uuid.UUID
    full_name: str
    email: str | None

    model_config = {"from_attributes": True}
