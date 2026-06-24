# =============================================================================
# Jersey Ice Cream Platform — Base Repository
# =============================================================================
# Generic CRUD repository providing type-safe database operations.
#
# Design Decision:
#   Repository pattern separates data access from business logic.
#   The service layer calls repositories; repositories handle SQL.
#   This enables:
#   1. Easy testing (mock repositories instead of database)
#   2. Consistent query patterns (pagination, soft-delete, audit)
#   3. Single place to add query optimization
#
# DSA:
#   - list_all with pagination: O(log n + k) where k = page_size (B-tree index scan)
#   - get_by_id: O(log n) single index lookup
#   - create: O(log n) for index insertion
#   - Soft delete filter: O(1) additional predicate on indexed column
# =============================================================================

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseModel
from app.schemas.common import PaginationMeta, PaginationParams

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Generic async CRUD repository.

    Subclass for entity-specific queries:
        class DistributorRepo(BaseRepository[Distributor]):
            model = Distributor

            async def find_by_city(self, db, city):
                ...
    """

    model: type[ModelType]

    def __init__(self) -> None:
        if not hasattr(self, "model"):
            raise NotImplementedError("Subclass must define 'model' class attribute")

    # ─── Read Operations ────────────────────────────────────────────────

    async def get_by_id(
        self,
        db: AsyncSession,
        entity_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> ModelType | None:
        """
        Fetch a single entity by ID.

        Time Complexity: O(log n) — primary key index lookup.
        """
        query = select(self.model).where(self.model.id == entity_id)
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        db: AsyncSession,
        *,
        pagination: PaginationParams | None = None,
        filters: dict[str, Any] | None = None,
        order_by: str = "created_at",
        order_desc: bool = True,
        include_deleted: bool = False,
    ) -> tuple[list[ModelType], PaginationMeta]:
        """
        List entities with pagination, filtering, and sorting.

        Returns:
            Tuple of (items, pagination_meta)

        Time Complexity: O(log n + k) where k = page_size
        """
        pagination = pagination or PaginationParams()

        # Build base query
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        # Soft delete filter
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
            count_query = count_query.where(self.model.deleted_at.is_(None))

        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    column = getattr(self.model, field)
                    if isinstance(value, list):
                        query = query.where(column.in_(value))
                        count_query = count_query.where(column.in_(value))
                    else:
                        query = query.where(column == value)
                        count_query = count_query.where(column == value)

        # Get total count
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        if hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            query = query.order_by(order_column.desc() if order_desc else order_column.asc())

        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)

        # Execute
        result = await db.execute(query)
        items = list(result.scalars().all())

        # Build pagination meta
        total_pages = max(1, (total + pagination.page_size - 1) // pagination.page_size)
        meta = PaginationMeta(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_prev=pagination.page > 1,
        )

        return items, meta

    async def exists(
        self,
        db: AsyncSession,
        entity_id: uuid.UUID,
    ) -> bool:
        """Check if entity exists. O(log n)."""
        query = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.id == entity_id)
            .where(self.model.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return (result.scalar() or 0) > 0

    async def count(
        self,
        db: AsyncSession,
        *,
        filters: dict[str, Any] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Count entities matching filters. O(n) worst case, O(log n) with indexed filter."""
        query = select(func.count()).select_from(self.model)
        if not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)
        result = await db.execute(query)
        return result.scalar() or 0

    # ─── Write Operations ───────────────────────────────────────────────

    async def create(
        self,
        db: AsyncSession,
        **kwargs: Any,
    ) -> ModelType:
        """
        Create a new entity.

        Time Complexity: O(log n) for index insertion per indexed column.
        """
        entity = self.model(**kwargs)
        db.add(entity)
        await db.flush()  # Get the ID without committing
        await db.refresh(entity)
        return entity

    async def update(
        self,
        db: AsyncSession,
        entity: ModelType,
        **kwargs: Any,
    ) -> ModelType:
        """
        Update an existing entity.

        Only updates provided fields (partial update).
        """
        for field, value in kwargs.items():
            if hasattr(entity, field) and value is not None:
                setattr(entity, field, value)
        await db.flush()
        await db.refresh(entity)
        return entity

    async def soft_delete(
        self,
        db: AsyncSession,
        entity: ModelType,
    ) -> ModelType:
        """
        Soft-delete an entity by setting deleted_at.

        Data is preserved for audit and recovery.
        """
        entity.soft_delete()
        await db.flush()
        return entity

    async def hard_delete(
        self,
        db: AsyncSession,
        entity: ModelType,
    ) -> None:
        """
        Permanently delete an entity. Use with extreme caution.

        Only for: test data cleanup, GDPR erasure requests.
        """
        await db.delete(entity)
        await db.flush()

    async def bulk_create(
        self,
        db: AsyncSession,
        items: list[dict[str, Any]],
    ) -> list[ModelType]:
        """
        Bulk create entities. More efficient than individual creates.

        Time Complexity: O(m × log n) where m = number of items.
        """
        entities = [self.model(**item) for item in items]
        db.add_all(entities)
        await db.flush()
        for entity in entities:
            await db.refresh(entity)
        return entities
