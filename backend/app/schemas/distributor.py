# =============================================================================
# Jersey Ice Cream Platform — Distributor Schemas
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import GeoPoint


# ─── Distributor Schemas ─────────────────────────────────────────────────────


class DistributorCreate(BaseModel):
    """Create a new distributor."""

    company_name: str = Field(min_length=2, max_length=255)
    legal_name: str | None = None
    gstin: str | None = Field(default=None, max_length=15)
    pan: str | None = Field(default=None, max_length=10)
    contact_phone: str = Field(min_length=10, max_length=20)
    contact_email: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    headquarters_location: GeoPoint | None = None
    credit_limit: float = Field(default=0.0, ge=0)
    commission_rate: float = Field(default=0.0, ge=0, le=100)


class DistributorUpdate(BaseModel):
    """Update distributor fields (partial update)."""

    company_name: str | None = None
    legal_name: str | None = None
    gstin: str | None = None
    pan: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    headquarters_location: GeoPoint | None = None
    status: str | None = None
    credit_limit: float | None = None
    commission_rate: float | None = None


class DistributorResponse(BaseModel):
    """Distributor detail response."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    company_name: str
    legal_name: str | None
    gstin: str | None
    pan: str | None
    contact_phone: str
    contact_email: str | None
    address: str | None
    city: str | None
    state: str | None
    pincode: str | None
    status: str
    credit_limit: float
    outstanding_balance: float
    commission_rate: float
    created_at: datetime
    updated_at: datetime

    # Computed fields
    territory_count: int = 0
    warehouse_count: int = 0
    active_cart_count: int = 0

    model_config = {"from_attributes": True}


class DistributorListResponse(BaseModel):
    """Compact distributor for list views."""

    id: uuid.UUID
    company_name: str
    city: str | None
    state: str | None
    status: str
    contact_phone: str
    territory_count: int = 0
    active_cart_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Territory Schemas ───────────────────────────────────────────────────────


class TerritoryCreate(BaseModel):
    """Create a new territory."""

    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=2, max_length=20)
    geohash_prefix: str | None = None
    population_estimate: int | None = None
    area_sq_km: float | None = None
    demographics: dict | None = None


class TerritoryResponse(BaseModel):
    """Territory detail response."""

    id: uuid.UUID
    distributor_id: uuid.UUID
    name: str
    code: str
    geohash_prefix: str | None
    population_estimate: int | None
    area_sq_km: float | None
    demographics: dict | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Warehouse Schemas ───────────────────────────────────────────────────────


class WarehouseCreate(BaseModel):
    """Create a new warehouse."""

    name: str = Field(min_length=2, max_length=255)
    address: str | None = None
    location: GeoPoint | None = None
    capacity_liters: float = Field(ge=0)
    cold_storage_type: str = "deep_freezer"
    target_temp_celsius: float = -20.0


class WarehouseResponse(BaseModel):
    """Warehouse detail response."""

    id: uuid.UUID
    distributor_id: uuid.UUID
    name: str
    address: str | None
    capacity_liters: float
    used_capacity_liters: float
    capacity_utilization: float
    cold_storage_type: str
    target_temp_celsius: float
    current_temp_celsius: float | None
    is_temp_safe: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
