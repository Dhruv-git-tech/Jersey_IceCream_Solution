# =============================================================================
# Jersey Ice Cream Platform — User Repository
# =============================================================================

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Find user by email address. O(log n) via unique index."""
        query = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.email == email)
            .where(User.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_phone(self, db: AsyncSession, phone: str) -> User | None:
        """Find user by phone number. O(log n) via unique index."""
        query = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.phone == phone)
            .where(User.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_with_roles(self, db: AsyncSession, user_id) -> User | None:
        """Fetch user with eagerly loaded roles. O(log n) + join."""
        query = (
            select(User)
            .options(joinedload(User.roles))
            .where(User.id == user_id)
            .where(User.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.unique().scalar_one_or_none()

    async def email_exists(self, db: AsyncSession, email: str) -> bool:
        """Check if email is already registered."""
        from sqlalchemy import func

        query = (
            select(func.count())
            .select_from(User)
            .where(User.email == email)
            .where(User.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return (result.scalar() or 0) > 0

    async def phone_exists(self, db: AsyncSession, phone: str) -> bool:
        """Check if phone is already registered."""
        from sqlalchemy import func

        query = (
            select(func.count())
            .select_from(User)
            .where(User.phone == phone)
            .where(User.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return (result.scalar() or 0) > 0

    async def increment_failed_login(self, db: AsyncSession, user: User) -> None:
        """Increment failed login counter for lockout policy."""
        user.failed_login_attempts += 1
        await db.flush()

    async def reset_failed_login(self, db: AsyncSession, user: User) -> None:
        """Reset failed login counter after successful login."""
        user.failed_login_attempts = 0
        await db.flush()

    async def update_last_login(self, db: AsyncSession, user: User) -> None:
        """Record last login timestamp."""
        from datetime import UTC, datetime

        user.last_login = datetime.now(UTC).isoformat()
        await db.flush()
