# =============================================================================
# Jersey Ice Cream Platform — Product & Inventory Models
# =============================================================================

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ProductCategory(str, enum.Enum):
    CONE = "cone"
    CUP = "cup"
    BAR = "bar"
    STICK = "stick"
    SANDWICH = "sandwich"
    FAMILY_PACK = "family_pack"
    BULK = "bulk"
    KULFI = "kulfi"
    NOVELTY = "novelty"
    PREMIUM = "premium"


class UpdateSource(str, enum.Enum):
    """How inventory data was updated."""
    MANUAL = "manual"
    PHOTO_ANALYSIS = "photo_analysis"
    REFILL_DELIVERY = "refill_delivery"
    ORDER_DISPATCH = "order_dispatch"
    SYSTEM_ESTIMATE = "system_estimate"
    WHATSAPP = "whatsapp"


class Product(BaseModel):
    """
    Ice cream product (SKU) in the catalog.

    Products are managed centrally by the company.
    Each product has:
    - Unique SKU code
    - Category classification (for AI detection training)
    - Pricing at multiple levels (MRP, distributor, vendor)
    - Weight for cold chain logistics calculations
    - Shelf life for expiry/wastage tracking
    """

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[ProductCategory] = mapped_column(
        Enum(ProductCategory, name="product_category"),
        nullable=False,
        index=True,
    )
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    brand: Mapped[str] = mapped_column(String(100), default="Jersey", nullable=False)

    # Pricing (INR)
    mrp: Mapped[float] = mapped_column(Float, nullable=False)
    distributor_price: Mapped[float] = mapped_column(Float, nullable=False)
    vendor_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Physical attributes
    weight_grams: Mapped[float] = mapped_column(Float, nullable=False)
    volume_ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    serving_size: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Storage
    shelf_life_days: Mapped[int] = mapped_column(Integer, default=180)
    storage_temp_min_celsius: Mapped[float] = mapped_column(Float, default=-25.0)
    storage_temp_max_celsius: Mapped[float] = mapped_column(Float, default=-18.0)

    # Media
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
    is_seasonal: Mapped[bool] = mapped_column(default=False)
    season_start_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_end_month: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # AI detection
    yolo_class_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Maps to YOLO class index
    detection_keywords: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # Alt text for detection

    nutritional_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<Product(sku={self.sku}, name={self.name})>"


class WarehouseInventory(BaseModel):
    """
    Current inventory levels at a warehouse.

    One row per (warehouse, product) combination.
    Updated on:
    - Inbound shipment from factory
    - Outbound dispatch to cart/vendor
    - Stock audit / adjustment

    Reorder level triggers automated refill suggestions.
    """

    __tablename__ = "warehouse_inventory"
    __table_args__ = (
        # Each product appears once per warehouse
        {"schema": None},
    )

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_quantity: Mapped[int] = mapped_column(
        Integer, default=0
    )  # Allocated to pending orders
    reorder_level: Mapped[int] = mapped_column(Integer, default=50)
    max_stock_level: Mapped[int] = mapped_column(Integer, default=500)
    batch_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_restocked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_dispatched: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="inventory")
    product: Mapped["Product"] = relationship("Product", lazy="joined")

    @property
    def available_quantity(self) -> int:
        """Quantity available for dispatch (total - reserved)."""
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def needs_reorder(self) -> bool:
        """Check if available stock is below reorder level."""
        return self.available_quantity <= self.reorder_level

    @property
    def stock_health(self) -> str:
        """Categorize stock health for dashboard display."""
        if self.available_quantity == 0:
            return "stockout"
        if self.needs_reorder:
            return "low"
        if self.available_quantity > self.max_stock_level * 0.8:
            return "excess"
        return "healthy"

    def __repr__(self) -> str:
        return f"<WarehouseInventory(warehouse={self.warehouse_id}, product={self.product_id}, qty={self.quantity})>"


class CartInventory(BaseModel):
    """
    Estimated inventory at a push cart.

    Key design: No mandatory manual entry.
    Quantities are estimated from:
    1. AI photo analysis (primary source)
    2. Refill delivery records
    3. Time-based decay (sales velocity model)

    Sales velocity is an exponential moving average updated each time
    a new inventory snapshot is received.
    """

    __tablename__ = "cart_inventory"

    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    estimated_quantity: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(
        Float, default=0.5
    )  # 0.0 to 1.0 confidence in estimate
    sales_velocity_per_hour: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # Units sold per hour (EMA)
    last_photo_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_refill_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    update_source: Mapped[UpdateSource] = mapped_column(
        Enum(UpdateSource, name="update_source"),
        default=UpdateSource.SYSTEM_ESTIMATE,
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", lazy="joined")

    @property
    def is_stockout(self) -> bool:
        return self.estimated_quantity <= 0

    @property
    def estimated_hours_until_stockout(self) -> float | None:
        """Estimate hours until this product runs out at current velocity."""
        if self.sales_velocity_per_hour <= 0:
            return None  # Can't estimate
        if self.estimated_quantity <= 0:
            return 0.0
        return round(self.estimated_quantity / self.sales_velocity_per_hour, 1)

    def __repr__(self) -> str:
        return f"<CartInventory(cart={self.cart_id}, product={self.product_id}, qty={self.estimated_quantity})>"
