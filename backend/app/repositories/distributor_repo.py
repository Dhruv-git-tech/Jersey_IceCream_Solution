# =============================================================================
# Jersey Ice Cream Platform — Distributor Repository
# =============================================================================

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.cart import Cart, CartStatus
from app.models.distributor import Distributor, Territory, Warehouse
from app.repositories.base import BaseRepository


class DistributorRepository(BaseRepository[Distributor]):
    model = Distributor

    async def get_with_relations(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
    ) -> Distributor | None:
        """Fetch distributor with territories and warehouses eagerly loaded."""
        query = (
            select(Distributor)
            .options(
                joinedload(Distributor.territories),
                joinedload(Distributor.warehouses),
            )
            .where(Distributor.id == distributor_id)
            .where(Distributor.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_gstin(self, db: AsyncSession, gstin: str) -> Distributor | None:
        """Find distributor by GSTIN. O(log n) via unique index."""
        query = (
            select(Distributor)
            .where(Distributor.gstin == gstin)
            .where(Distributor.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, db: AsyncSession, user_id: uuid.UUID) -> Distributor | None:
        """Find distributor by linked user account."""
        query = (
            select(Distributor)
            .where(Distributor.user_id == user_id)
            .where(Distributor.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_cart_count(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
    ) -> int:
        """Count active carts for a distributor."""
        query = (
            select(func.count())
            .select_from(Cart)
            .where(Cart.distributor_id == distributor_id)
            .where(Cart.status == CartStatus.ACTIVE)
            .where(Cart.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.scalar() or 0

    async def get_territory_count(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
    ) -> int:
        """Count territories for a distributor."""
        query = (
            select(func.count())
            .select_from(Territory)
            .where(Territory.distributor_id == distributor_id)
            .where(Territory.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.scalar() or 0

    async def search_by_name(
        self,
        db: AsyncSession,
        query_str: str,
        limit: int = 20,
    ) -> list[Distributor]:
        """Full-text search on company name. O(n) without FTS index."""
        query = (
            select(Distributor)
            .where(Distributor.company_name.ilike(f"%{query_str}%"))
            .where(Distributor.deleted_at.is_(None))
            .limit(limit)
        )
        result = await db.execute(query)
        return list(result.scalars().all())


class TerritoryRepository(BaseRepository[Territory]):
    model = Territory

    async def get_by_code(self, db: AsyncSession, code: str) -> Territory | None:
        """Find territory by unique code."""
        query = (
            select(Territory)
            .where(Territory.code == code)
            .where(Territory.deleted_at.is_(None))
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_distributor(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
    ) -> list[Territory]:
        """Get all territories for a distributor."""
        query = (
            select(Territory)
            .where(Territory.distributor_id == distributor_id)
            .where(Territory.deleted_at.is_(None))
            .order_by(Territory.name)
        )
        result = await db.execute(query)
        return list(result.scalars().all())


class WarehouseRepository(BaseRepository[Warehouse]):
    model = Warehouse

    async def get_by_distributor(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
    ) -> list[Warehouse]:
        """Get all warehouses for a distributor."""
        query = (
            select(Warehouse)
            .where(Warehouse.distributor_id == distributor_id)
            .where(Warehouse.deleted_at.is_(None))
            .order_by(Warehouse.name)
        )
        result = await db.execute(query)
        return list(result.scalars().all())
