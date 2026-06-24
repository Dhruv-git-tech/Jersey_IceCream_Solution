# =============================================================================
# Jersey Ice Cream Platform — Distributor, Territory, Warehouse Models
# =============================================================================

from __future__ import annotations

import enum
import uuid

from geoalchemy2 import Geography, Geometry
from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class DistributorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ONBOARDING = "onboarding"


class ColdStorageType(str, enum.Enum):
    DEEP_FREEZER = "deep_freezer"          # -18°C to -25°C
    WALK_IN_COOLER = "walk_in_cooler"      # 0°C to 4°C
    BLAST_FREEZER = "blast_freezer"        # -30°C to -40°C
    COMBINATION = "combination"


class Distributor(BaseModel):
    """
    Ice cream distributor / dealer entity.

    A distributor:
    - Manages one or more warehouses
    - Supplies ice cream to multiple carts/vendors
    - Operates within assigned territories
    - Places refill orders with the central company

    Onboarding Flow:
        ONBOARDING → (KYC verification) → ACTIVE
        ACTIVE → (policy violation) → SUSPENDED
        ACTIVE → (contract end) → INACTIVE
    """

    __tablename__ = "distributors"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gstin: Mapped[str | None] = mapped_column(
        String(15), unique=True, nullable=True
    )  # GST Identification Number (India)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True)  # PAN card
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # PostGIS point for headquarters
    headquarters_location: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
    )

    status: Mapped[DistributorStatus] = mapped_column(
        Enum(DistributorStatus, name="distributor_status"),
        default=DistributorStatus.ONBOARDING,
        nullable=False,
        index=True,
    )
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0)
    outstanding_balance: Mapped[float] = mapped_column(Float, default=0.0)
    commission_rate: Mapped[float] = mapped_column(Float, default=0.0)  # Percentage
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="joined")
    territories: Mapped[list["Territory"]] = relationship(
        "Territory", back_populates="distributor", cascade="all, delete-orphan"
    )
    warehouses: Mapped[list["Warehouse"]] = relationship(
        "Warehouse", back_populates="distributor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Distributor(company={self.company_name}, status={self.status})>"


class Territory(BaseModel):
    """
    Geographic territory assigned to a distributor.

    Territories are non-overlapping polygons that define a distributor's
    service area. Used for:
    - Assigning carts to nearest distributor
    - Demand forecasting at territory level
    - Performance benchmarking between territories

    Geohash prefix enables efficient spatial queries:
    - Prefix length 4 (~39km × 20km) for territory grouping
    - Used as partition key for demand forecasts
    """

    __tablename__ = "territories"

    distributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("distributors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # PostGIS polygon for territory boundary
    boundary: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POLYGON", srid=4326),
        nullable=True,
    )

    geohash_prefix: Mapped[str | None] = mapped_column(
        String(12), nullable=True, index=True
    )
    population_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_sq_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    demographics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)

    # Relationships
    distributor: Mapped["Distributor"] = relationship(
        "Distributor", back_populates="territories"
    )

    def __repr__(self) -> str:
        return f"<Territory(name={self.name}, code={self.code})>"


class Warehouse(BaseModel):
    """
    Cold storage warehouse managed by a distributor.

    Temperature monitoring is critical for ice cream storage:
    - Deep freezer: -18°C to -25°C (ideal for long-term storage)
    - Walk-in cooler: 0°C to 4°C (for loading/dispatch area)
    - Blast freezer: -30°C to -40°C (for fresh stock)

    Temperature alerts trigger when current_temp deviates from safe range.
    """

    __tablename__ = "warehouses"

    distributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("distributors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # PostGIS point for warehouse location
    location: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
    )

    capacity_liters: Mapped[float] = mapped_column(Float, default=0.0)
    used_capacity_liters: Mapped[float] = mapped_column(Float, default=0.0)
    cold_storage_type: Mapped[ColdStorageType] = mapped_column(
        Enum(ColdStorageType, name="cold_storage_type"),
        default=ColdStorageType.DEEP_FREEZER,
        nullable=False,
    )
    target_temp_celsius: Mapped[float] = mapped_column(Float, default=-20.0)
    current_temp_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    distributor: Mapped["Distributor"] = relationship(
        "Distributor", back_populates="warehouses"
    )
    inventory: Mapped[list["WarehouseInventory"]] = relationship(
        "WarehouseInventory", back_populates="warehouse", cascade="all, delete-orphan"
    )

    @property
    def capacity_utilization(self) -> float:
        """Calculate capacity utilization percentage."""
        if self.capacity_liters == 0:
            return 0.0
        return round((self.used_capacity_liters / self.capacity_liters) * 100, 2)

    @property
    def is_temp_safe(self) -> bool:
        """Check if current temperature is within safe range."""
        if self.current_temp_celsius is None:
            return False  # No reading = unsafe
        # Allow ±3°C tolerance from target
        return abs(self.current_temp_celsius - self.target_temp_celsius) <= 3.0

    def __repr__(self) -> str:
        return f"<Warehouse(name={self.name}, type={self.cold_storage_type})>"
