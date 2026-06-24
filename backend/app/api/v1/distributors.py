# =============================================================================
# Jersey Ice Cream Platform — Distributor API Routes
# =============================================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Permission
from app.database import get_db_session
from app.dependencies import CurrentUserId, require_permission
from app.schemas.common import PaginatedResponse, PaginationParams
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
from app.schemas.common import MessageResponse
from app.services.distributor_service import DistributorService

router = APIRouter(prefix="/distributors", tags=["Distributors"])
distributor_service = DistributorService()


# ─── Distributor CRUD ────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=DistributorResponse,
    status_code=201,
    summary="Create a distributor",
    description="Register a new ice cream distributor. Requires DISTRIBUTORS_CREATE permission.",
    dependencies=[Depends(require_permission(Permission.DISTRIBUTORS_CREATE))],
)
async def create_distributor(
    data: DistributorCreate,
    user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db_session),
) -> DistributorResponse:
    """Create a new distributor."""
    return await distributor_service.create_distributor(db, data, created_by_user_id=user_id)


@router.get(
    "",
    response_model=PaginatedResponse[DistributorListResponse],
    summary="List distributors",
    description="List distributors with filtering, searching, and pagination.",
    dependencies=[Depends(require_permission(Permission.DISTRIBUTORS_READ))],
)
async def list_distributors(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: str | None = Query(None, description="Filter by status"),
    city: str | None = Query(None, description="Filter by city"),
    state: str | None = Query(None, description="Filter by state"),
    search: str | None = Query(None, description="Search company name"),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[DistributorListResponse]:
    """List distributors with optional filters."""
    pagination = PaginationParams(page=page, page_size=page_size)
    return await distributor_service.list_distributors(
        db,
        pagination,
        status=status,
        city=city,
        state=state,
        search=search,
    )


@router.get(
    "/{distributor_id}",
    response_model=DistributorResponse,
    summary="Get distributor details",
    description="Get detailed information about a specific distributor.",
    dependencies=[Depends(require_permission(Permission.DISTRIBUTORS_READ))],
)
async def get_distributor(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> DistributorResponse:
    """Get distributor by ID."""
    return await distributor_service.get_distributor(db, distributor_id)


@router.patch(
    "/{distributor_id}",
    response_model=DistributorResponse,
    summary="Update distributor",
    description="Update distributor fields. Partial update — only send fields to change.",
    dependencies=[Depends(require_permission(Permission.DISTRIBUTORS_UPDATE))],
)
async def update_distributor(
    distributor_id: uuid.UUID,
    data: DistributorUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> DistributorResponse:
    """Update distributor."""
    return await distributor_service.update_distributor(db, distributor_id, data)


@router.delete(
    "/{distributor_id}",
    response_model=MessageResponse,
    summary="Delete distributor",
    description="Soft-delete a distributor. Cannot delete with active carts.",
    dependencies=[Depends(require_permission(Permission.DISTRIBUTORS_DELETE))],
)
async def delete_distributor(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Delete (soft) a distributor."""
    await distributor_service.delete_distributor(db, distributor_id)
    return MessageResponse(message="Distributor deleted successfully")


# ─── Territory Endpoints ─────────────────────────────────────────────────────


@router.post(
    "/{distributor_id}/territories",
    response_model=TerritoryResponse,
    status_code=201,
    summary="Create territory",
    description="Create a new territory for a distributor.",
    dependencies=[Depends(require_permission(Permission.DISTRIBUTORS_MANAGE))],
)
async def create_territory(
    distributor_id: uuid.UUID,
    data: TerritoryCreate,
    db: AsyncSession = Depends(get_db_session),
) -> TerritoryResponse:
    """Create a territory for a distributor."""
    return await distributor_service.create_territory(db, distributor_id, data)


@router.get(
    "/{distributor_id}/territories",
    response_model=list[TerritoryResponse],
    summary="List territories",
    description="List all territories for a distributor.",
    dependencies=[Depends(require_permission(Permission.DISTRIBUTORS_READ))],
)
async def list_territories(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[TerritoryResponse]:
    """List territories for a distributor."""
    return await distributor_service.list_territories(db, distributor_id)


# ─── Warehouse Endpoints ─────────────────────────────────────────────────────


@router.post(
    "/{distributor_id}/warehouses",
    response_model=WarehouseResponse,
    status_code=201,
    summary="Create warehouse",
    description="Create a new cold storage warehouse for a distributor.",
    dependencies=[Depends(require_permission(Permission.DISTRIBUTORS_MANAGE))],
)
async def create_warehouse(
    distributor_id: uuid.UUID,
    data: WarehouseCreate,
    db: AsyncSession = Depends(get_db_session),
) -> WarehouseResponse:
    """Create a warehouse for a distributor."""
    return await distributor_service.create_warehouse(db, distributor_id, data)


@router.get(
    "/{distributor_id}/warehouses",
    response_model=list[WarehouseResponse],
    summary="List warehouses",
    description="List all warehouses for a distributor.",
    dependencies=[Depends(require_permission(Permission.DISTRIBUTORS_READ))],
)
async def list_warehouses(
    distributor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[WarehouseResponse]:
    """List warehouses for a distributor."""
    return await distributor_service.list_warehouses(db, distributor_id)
