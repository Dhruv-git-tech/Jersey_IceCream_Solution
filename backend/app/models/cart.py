# =============================================================================
# Jersey Ice Cream Platform — Cart & Vendor Models
# =============================================================================

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class CartType(str, enum.Enum):
    PUSH_CART = "push_cart"
    FREEZER_CART = "freezer_cart"
    TRICYCLE = "tricycle"
    KIOSK = "kiosk"
    MOBILE_VAN = "mobile_van"


class CartStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class RefillRequestSource(str, enum.Enum):
    WHATSAPP = "whatsapp"
    APP = "app"
    PHONE_CALL = "phone_call"
    AUTO_SYSTEM = "auto_system"  # System-generated based on AI prediction
    PHOTO_TRIGGER = "photo_trigger"  # Triggered by photo analysis showing low stock


class RefillRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RefillPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # Stockout detected


class PhotoProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class Cart(BaseModel):
    """
    Push cart / vendor point-of-sale unit.

    Each cart is a node in the swarm intelligence network.
    GPS location is updated every 5 minutes via lightweight HTTP ping.
    Geohash is pre-computed for efficient spatial queries.

    Cart lifecycle:
        Registration → ACTIVE → (breakdown) → MAINTENANCE → ACTIVE
        ACTIVE → (end of season) → INACTIVE
        MAINTENANCE → (beyond repair) → DECOMMISSIONED
    """

    __tablename__ = "carts"

    distributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("distributors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cart_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )

    # GPS & Location
    current_location: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_geohash: Mapped[str | None] = mapped_column(
        String(12), nullable=True, index=True
    )  # Precision 7 (~150m)
    last_location_update: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Cart details
    cart_type: Mapped[CartType] = mapped_column(
        Enum(CartType, name="cart_type"),
        default=CartType.PUSH_CART,
        nullable=False,
    )
    status: Mapped[CartStatus] = mapped_column(
        Enum(CartStatus, name="cart_status"),
        default=CartStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    capacity_units: Mapped[int] = mapped_column(
        Integer, default=100
    )  # Max products the cart can hold
    has_solar_panel: Mapped[bool] = mapped_column(default=False)
    battery_level: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100%

    # Operating info
    operating_hours_start: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )  # "09:00"
    operating_hours_end: Mapped[str | None] = mapped_column(
        String(5), nullable=True
    )  # "21:00"
    assigned_area_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    territory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("territories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    last_ping: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    # Relationships
    distributor: Mapped["Distributor"] = relationship("Distributor", lazy="joined")
    vendor: Mapped["User"] = relationship("User", foreign_keys=[vendor_id], lazy="joined")
    inventory: Mapped[list["CartInventory"]] = relationship(
        "CartInventory", cascade="all, delete-orphan"
    )
    photos: Mapped[list["CartPhoto"]] = relationship(
        "CartPhoto", back_populates="cart", cascade="all, delete-orphan"
    )
    refill_requests: Mapped[list["RefillRequest"]] = relationship(
        "RefillRequest", back_populates="cart", cascade="all, delete-orphan"
    )

    @property
    def is_online(self) -> bool:
        """Cart is considered online if pinged within last 15 minutes."""
        if self.last_ping is None:
            return False
        from datetime import UTC

        delta = datetime.now(UTC) - self.last_ping
        return delta.total_seconds() < 900  # 15 minutes

    def __repr__(self) -> str:
        return f"<Cart(code={self.cart_code}, status={self.status})>"


class CartLocationHistory(BaseModel):
    """
    Historical GPS locations for a cart.

    High-volume table: 10,000 carts × 288 pings/day = 2.88M rows/day
    Partitioned monthly by recorded_at.
    BRIN index on recorded_at for efficient range scans.

    DSA: Geohash enables O(1) encode + B-tree prefix queries for spatial lookups.
    """

    __tablename__ = "cart_location_history"

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location: Mapped[str] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geohash: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<CartLocationHistory(cart={self.cart_id}, geohash={self.geohash})>"


class CartPhoto(BaseModel):
    """
    Cart photo for AI vision analysis.

    Photos are uploaded by vendors via WhatsApp or mobile app.
    Stored in MinIO (S3-compatible).
    Processed asynchronously via Kafka → Vision Worker → YOLO inference.
    """

    __tablename__ = "cart_photos"

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    processing_status: Mapped[PhotoProcessingStatus] = mapped_column(
        Enum(PhotoProcessingStatus, name="photo_processing_status"),
        default=PhotoProcessingStatus.PENDING,
        nullable=False,
        index=True,
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    cart: Mapped["Cart"] = relationship("Cart", back_populates="photos")
    analysis_result: Mapped["PhotoAnalysisResult | None"] = relationship(
        "PhotoAnalysisResult",
        back_populates="photo",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CartPhoto(cart={self.cart_id}, status={self.processing_status})>"


class PhotoAnalysisResult(BaseModel):
    """
    AI vision analysis output for a cart photo.

    Stores:
    - Detected products with bounding boxes and confidence scores
    - Aggregated product counts
    - Total unit count
    - Overall confidence score
    - Model version for reproducibility
    - Processing time for performance monitoring
    """

    __tablename__ = "photo_analysis_results"

    photo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cart_photos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Detection results
    detected_products: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )  # [{class: "cone_vanilla", confidence: 0.92, bbox: [x,y,w,h]}, ...]
    product_counts: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # {"cone_vanilla": 5, "cup_chocolate": 3, ...}
    total_units: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Comparison with previous snapshot
    previous_total_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_sold_since_last: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delta_products: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Changes per product type

    # Model info
    model_name: Mapped[str] = mapped_column(String(100), default="yolov11-m-jersey")
    model_version: Mapped[str] = mapped_column(String(50), default="0.1.0")
    processing_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    photo: Mapped["CartPhoto"] = relationship("CartPhoto", back_populates="analysis_result")

    def __repr__(self) -> str:
        return f"<PhotoAnalysisResult(photo={self.photo_id}, total_units={self.total_units})>"


class RefillRequest(BaseModel):
    """
    Vendor's request for cart refill from distributor.

    Requests can be:
    - Manual (vendor via WhatsApp/app)
    - Auto-generated (system detects low stock via photo analysis)
    - Photo-triggered (AI detects stockout during photo processing)

    Priority calculation:
    - CRITICAL: Stockout detected (0 units)
    - HIGH: Below 20% capacity + high demand forecast
    - MEDIUM: Below 50% capacity
    - LOW: Below 70% capacity (preemptive)
    """

    __tablename__ = "refill_requests"

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    distributor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("distributors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    source: Mapped[RefillRequestSource] = mapped_column(
        Enum(RefillRequestSource, name="refill_request_source"),
        nullable=False,
    )
    status: Mapped[RefillRequestStatus] = mapped_column(
        Enum(RefillRequestStatus, name="refill_request_status"),
        default=RefillRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority: Mapped[RefillPriority] = mapped_column(
        Enum(RefillPriority, name="refill_priority"),
        default=RefillPriority.MEDIUM,
        nullable=False,
        index=True,
    )

    requested_products: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # {"product_id": quantity, ...}
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    cart: Mapped["Cart"] = relationship("Cart", back_populates="refill_requests")
    distributor: Mapped["Distributor"] = relationship("Distributor")

    @property
    def fulfillment_time_minutes(self) -> float | None:
        """Time from request to delivery in minutes."""
        if self.requested_at and self.delivered_at:
            delta = self.delivered_at - self.requested_at
            return round(delta.total_seconds() / 60, 1)
        return None

    def __repr__(self) -> str:
        return f"<RefillRequest(cart={self.cart_id}, status={self.status}, priority={self.priority})>"
