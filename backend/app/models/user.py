# =============================================================================
# Jersey Ice Cream Platform — User & Role Models
# =============================================================================

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, Base, TimestampMixin


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


# ─── Association Table: User ↔ Role (Many-to-Many) ──────────────────────────

user_roles = Table(
    "user_roles",
    Base.metadata,
    mapped_column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    mapped_column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(BaseModel):
    """
    RBAC role definition.

    Roles are predefined but stored in DB for flexibility.
    Permissions are stored as JSONB array for extensibility without migrations.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permissions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    is_system: Mapped[bool] = mapped_column(default=False)  # System roles can't be deleted

    # Relationships
    users: Mapped[list[User]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role(name={self.name})>"


class User(BaseModel):
    """
    Platform user account.

    Supports multiple authentication methods:
    - Email + password (primary)
    - Phone + OTP (for vendors in field)
    - Future: OAuth2 (Google, Microsoft for enterprise SSO)

    Security:
    - password_hash never leaves the database
    - last_login tracked for security audit
    - failed_login_attempts for lockout policy
    """

    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status", create_constraint=True),
        default=UserStatus.PENDING_VERIFICATION,
        nullable=False,
        index=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_login: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="joined",  # Always load roles with user (needed for auth)
    )

    # Constraints
    __table_args__ = (
        # At least one of email or phone must be provided (enforced at app level)
    )

    @property
    def role_names(self) -> list[str]:
        """Get list of role names for JWT payload."""
        return [role.name for role in self.roles]

    def __repr__(self) -> str:
        return f"<User(email={self.email}, name={self.full_name})>"
