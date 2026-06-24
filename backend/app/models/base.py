# =============================================================================
# Jersey Ice Cream Platform — Base ORM Model
# =============================================================================
# All database models inherit from this base, providing:
#   - UUID primary key (avoids sequential ID enumeration attacks)
#   - Audit timestamps (created_at, updated_at)
#   - Soft delete (deleted_at) for data recovery
#   - Common query helpers
#
# Design Decision:
#   UUID v4 over auto-increment because:
#   1. No sequential enumeration (security)
#   2. Can generate IDs client-side (offline support for carts)
#   3. Safe for distributed systems (no sequence contention)
#   4. Tradeoff: 16 bytes vs 8 bytes, slightly slower index lookups
# =============================================================================

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Abstract base class for all ORM models.

    Provides:
        - Type-annotated column mapping (SQLAlchemy 2.0 style)
        - Common column definitions via mixins
    """

    pass


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete support.

    Records are never physically deleted — only marked with deleted_at.
    All queries should filter WHERE deleted_at IS NULL by default.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        self.deleted_at = None


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """
    Base model with UUID primary key, timestamps, and soft delete.

    All domain entity models should inherit from this.

    Table naming convention: lowercase plural (users, distributors, carts).
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
