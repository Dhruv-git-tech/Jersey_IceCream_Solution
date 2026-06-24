# =============================================================================
# Jersey Ice Cream Platform — Distributor Service
# =============================================================================
# Business logic for distributor management, territory assignment,
# and warehouse operations.
# =============================================================================

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import EventProducer, Topic, get_event_producer
from app.core.exceptions import (
    BusinessRuleError,
    DuplicateError,
    NotFoundError,
)
from app.models.distributor import Distributor, DistributorStatus
from app.repositories.distributor_repo import (
    DistributorRepository,
    TerritoryRepository,
    WarehouseRepository,
)
from app.schemas.common import PaginatedResponse, PaginationMeta, PaginationParams
from app.schemas.distributor import (
    DistributorCreate,
    DistributorListResponse,
    DistributorResponse,
    DistributorUpdate,
    TerritoryCreate,
    TerritoryResponse,
    WarehouseCreate,
    WarehouseResponse,
)

logger = logging.getLogger(__name__)


class DistributorService:
    """
    Distributor management service.

    Handles:
    - CRUD operations for distributors
    - Territory assignment
    - Warehouse management
    - Business rule enforcement
    - Event publishing for downstream consumers
    """

    def __init__(self) -> None:
        self.distributor_repo = DistributorRepository()
        self.territory_repo = TerritoryRepository()
        self.warehouse_repo = WarehouseRepository()

    # ─── Distributor CRUD ────────────────────────────────────────────────

    async def create_distributor(
        self,
        db: AsyncSession,
        data: DistributorCreate,
        created_by_user_id: uuid.UUID | None = None,
    ) -> DistributorResponse:
        """
        Create a new distributor.

        Business Rules:
        - GSTIN must be unique (if provided)
        - Company name must be unique within state
        - Initial status is ONBOARDING
        """
        # Check GSTIN uniqueness
        if data.gstin:
            existing = await self.distributor_repo.get_by_gstin(db, data.gstin)
            if existing:
                raise DuplicateError("Distributor", "GSTIN")

        # Build create kwargs
        create_kwargs = data.model_dump(exclude={"headquarters_location"})

        # Handle geo point
        if data.headquarters_location:
            from geoalchemy2.elements import WKTElement

            create_kwargs["headquarters_location"] = WKTElement(
                f"POINT({data.headquarters_location.longitude} {data.headquarters_location.latitude})",
                srid=4326,
            )

        create_kwargs["status"] = DistributorStatus.ONBOARDING

        distributor = await self.distributor_repo.create(db, **create_kwargs)

        # Publish event
        try:
            producer = await get_event_producer()
            await producer.publish(
                topic=Topic.AUDIT_EVENT,
                event_type="distributor.created",
                payload={
                    "distributor_id": str(distributor.id),
                    "company_name": distributor.company_name,
                    "created_by": str(created_by_user_id) if created_by_user_id else None,
                },
                entity_id=str(distributor.id),
                entity_type="distributor",
            )
        except Exception:
            logger.warning("Failed to publish distributor.created event", exc_info=True)

        logger.info(
            "Distributor created: id=%s name=%s",
            distributor.id,
            distributor.company_name,
        )

        return await self._to_response(db, distributor)

    async def get_distributor(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
    ) -> DistributorResponse:
        """Get distributor by ID with computed fields."""
        distributor = await self.distributor_repo.get_by_id(db, distributor_id)
        if not distributor:
            raise NotFoundError("Distributor", str(distributor_id))
        return await self._to_response(db, distributor)

    async def list_distributors(
        self,
        db: AsyncSession,
        pagination: PaginationParams,
        *,
        status: str | None = None,
        city: str | None = None,
        state: str | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[DistributorListResponse]:
        """
        List distributors with filtering and pagination.

        Filters:
        - status: Filter by distributor status
        - city/state: Geographic filter
        - search: Full-text search on company name
        """
        filters = {}
        if status:
            filters["status"] = DistributorStatus(status)
        if city:
            filters["city"] = city
        if state:
            filters["state"] = state

        if search:
            # Use search method for name matching
            items = await self.distributor_repo.search_by_name(db, search, limit=pagination.page_size)
            total = len(items)
            meta = PaginationMeta(
                total=total,
                page=1,
                page_size=pagination.page_size,
                total_pages=1,
                has_next=False,
                has_prev=False,
            )
        else:
            items, meta = await self.distributor_repo.list_all(
                db,
                pagination=pagination,
                filters=filters,
            )

        response_items = []
        for dist in items:
            territory_count = await self.distributor_repo.get_territory_count(db, dist.id)
            cart_count = await self.distributor_repo.get_active_cart_count(db, dist.id)
            response_items.append(
                DistributorListResponse(
                    id=dist.id,
                    company_name=dist.company_name,
                    city=dist.city,
                    state=dist.state,
                    status=dist.status.value,
                    contact_phone=dist.contact_phone,
                    territory_count=territory_count,
                    active_cart_count=cart_count,
                    created_at=dist.created_at,
                )
            )

        return PaginatedResponse[DistributorListResponse](
            items=response_items,
            pagination=meta,
        )

    async def update_distributor(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
        data: DistributorUpdate,
    ) -> DistributorResponse:
        """Update distributor fields."""
        distributor = await self.distributor_repo.get_by_id(db, distributor_id)
        if not distributor:
            raise NotFoundError("Distributor", str(distributor_id))

        # GSTIN uniqueness check
        if data.gstin and data.gstin != distributor.gstin:
            existing = await self.distributor_repo.get_by_gstin(db, data.gstin)
            if existing:
                raise DuplicateError("Distributor", "GSTIN")

        # Status transition validation
        if data.status:
            self._validate_status_transition(distributor.status, DistributorStatus(data.status))

        update_kwargs = data.model_dump(
            exclude_unset=True,
            exclude={"headquarters_location"},
        )

        if data.headquarters_location:
            from geoalchemy2.elements import WKTElement

            update_kwargs["headquarters_location"] = WKTElement(
                f"POINT({data.headquarters_location.longitude} {data.headquarters_location.latitude})",
                srid=4326,
            )

        # Convert status string to enum
        if "status" in update_kwargs and isinstance(update_kwargs["status"], str):
            update_kwargs["status"] = DistributorStatus(update_kwargs["status"])

        distributor = await self.distributor_repo.update(db, distributor, **update_kwargs)
        return await self._to_response(db, distributor)

    async def delete_distributor(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
    ) -> None:
        """Soft-delete a distributor."""
        distributor = await self.distributor_repo.get_by_id(db, distributor_id)
        if not distributor:
            raise NotFoundError("Distributor", str(distributor_id))

        # Business rule: Can't delete active distributor with active carts
        active_carts = await self.distributor_repo.get_active_cart_count(db, distributor_id)
        if active_carts > 0:
            raise BusinessRuleError(
                message=f"Cannot delete distributor with {active_carts} active carts. "
                "Reassign or deactivate carts first.",
            )

        await self.distributor_repo.soft_delete(db, distributor)
        logger.info("Distributor soft-deleted: id=%s", distributor_id)

    # ─── Territory Management ────────────────────────────────────────────

    async def create_territory(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
        data: TerritoryCreate,
    ) -> TerritoryResponse:
        """Create a new territory for a distributor."""
        # Verify distributor exists
        distributor = await self.distributor_repo.get_by_id(db, distributor_id)
        if not distributor:
            raise NotFoundError("Distributor", str(distributor_id))

        # Check territory code uniqueness
        existing = await self.territory_repo.get_by_code(db, data.code)
        if existing:
            raise DuplicateError("Territory", "code")

        territory = await self.territory_repo.create(
            db,
            distributor_id=distributor_id,
            **data.model_dump(),
        )

        return TerritoryResponse.model_validate(territory)

    async def list_territories(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
    ) -> list[TerritoryResponse]:
        """List all territories for a distributor."""
        territories = await self.territory_repo.get_by_distributor(db, distributor_id)
        return [TerritoryResponse.model_validate(t) for t in territories]

    # ─── Warehouse Management ────────────────────────────────────────────

    async def create_warehouse(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
        data: WarehouseCreate,
    ) -> WarehouseResponse:
        """Create a new warehouse for a distributor."""
        distributor = await self.distributor_repo.get_by_id(db, distributor_id)
        if not distributor:
            raise NotFoundError("Distributor", str(distributor_id))

        create_kwargs = data.model_dump(exclude={"location"})

        if data.location:
            from geoalchemy2.elements import WKTElement

            create_kwargs["location"] = WKTElement(
                f"POINT({data.location.longitude} {data.location.latitude})",
                srid=4326,
            )

        warehouse = await self.warehouse_repo.create(
            db,
            distributor_id=distributor_id,
            **create_kwargs,
        )

        return WarehouseResponse(
            id=warehouse.id,
            distributor_id=warehouse.distributor_id,
            name=warehouse.name,
            address=warehouse.address,
            capacity_liters=warehouse.capacity_liters,
            used_capacity_liters=warehouse.used_capacity_liters,
            capacity_utilization=warehouse.capacity_utilization,
            cold_storage_type=warehouse.cold_storage_type.value,
            target_temp_celsius=warehouse.target_temp_celsius,
            current_temp_celsius=warehouse.current_temp_celsius,
            is_temp_safe=warehouse.is_temp_safe,
            is_active=warehouse.is_active,
            created_at=warehouse.created_at,
        )

    async def list_warehouses(
        self,
        db: AsyncSession,
        distributor_id: uuid.UUID,
    ) -> list[WarehouseResponse]:
        """List all warehouses for a distributor."""
        warehouses = await self.warehouse_repo.get_by_distributor(db, distributor_id)
        return [
            WarehouseResponse(
                id=w.id,
                distributor_id=w.distributor_id,
                name=w.name,
                address=w.address,
                capacity_liters=w.capacity_liters,
                used_capacity_liters=w.used_capacity_liters,
                capacity_utilization=w.capacity_utilization,
                cold_storage_type=w.cold_storage_type.value,
                target_temp_celsius=w.target_temp_celsius,
                current_temp_celsius=w.current_temp_celsius,
                is_temp_safe=w.is_temp_safe,
                is_active=w.is_active,
                created_at=w.created_at,
            )
            for w in warehouses
        ]

    # ─── Helpers ─────────────────────────────────────────────────────────

    def _validate_status_transition(
        self,
        current: DistributorStatus,
        target: DistributorStatus,
    ) -> None:
        """Validate distributor status transitions."""
        valid_transitions = {
            DistributorStatus.ONBOARDING: {DistributorStatus.ACTIVE, DistributorStatus.INACTIVE},
            DistributorStatus.ACTIVE: {DistributorStatus.SUSPENDED, DistributorStatus.INACTIVE},
            DistributorStatus.SUSPENDED: {DistributorStatus.ACTIVE, DistributorStatus.INACTIVE},
            DistributorStatus.INACTIVE: {DistributorStatus.ACTIVE},
        }

        if target not in valid_transitions.get(current, set()):
            raise BusinessRuleError(
                message=f"Invalid status transition: {current.value} → {target.value}",
                details={
                    "current_status": current.value,
                    "target_status": target.value,
                    "valid_targets": [s.value for s in valid_transitions.get(current, set())],
                },
            )

    async def _to_response(
        self,
        db: AsyncSession,
        distributor: Distributor,
    ) -> DistributorResponse:
        """Convert Distributor model to response schema with computed fields."""
        territory_count = await self.distributor_repo.get_territory_count(db, distributor.id)
        cart_count = await self.distributor_repo.get_active_cart_count(db, distributor.id)

        return DistributorResponse(
            id=distributor.id,
            user_id=distributor.user_id,
            company_name=distributor.company_name,
            legal_name=distributor.legal_name,
            gstin=distributor.gstin,
            pan=distributor.pan,
            contact_phone=distributor.contact_phone,
            contact_email=distributor.contact_email,
            address=distributor.address,
            city=distributor.city,
            state=distributor.state,
            pincode=distributor.pincode,
            status=distributor.status.value,
            credit_limit=distributor.credit_limit,
            outstanding_balance=distributor.outstanding_balance,
            commission_rate=distributor.commission_rate,
            territory_count=territory_count,
            warehouse_count=len(distributor.warehouses) if distributor.warehouses else 0,
            active_cart_count=cart_count,
            created_at=distributor.created_at,
            updated_at=distributor.updated_at,
        )
