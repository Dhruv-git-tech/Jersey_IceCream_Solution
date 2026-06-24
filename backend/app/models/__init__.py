# =============================================================================
# Jersey Ice Cream Platform — Model Registry
# =============================================================================

from app.models.base import Base, BaseModel
from app.models.user import User, Role, user_roles, UserStatus
from app.models.distributor import (
    Distributor,
    DistributorStatus,
    Territory,
    Warehouse,
    ColdStorageType,
)
from app.models.product import (
    Product,
    ProductCategory,
    WarehouseInventory,
    CartInventory,
    UpdateSource,
)
from app.models.cart import (
    Cart,
    CartType,
    CartStatus,
    CartLocationHistory,
    CartPhoto,
    PhotoAnalysisResult,
    PhotoProcessingStatus,
    RefillRequest,
    RefillRequestSource,
    RefillRequestStatus,
    RefillPriority,
)
from app.models.order import (
    Order,
    OrderItem,
    OrderType,
    OrderStatus,
    PaymentStatus,
)
from app.models.forecast import (
    DemandForecast,
    ForecastHorizon,
    ExternalEvent,
    EventType,
    WeatherData,
    CompetitorIntel,
    CompetitorIntelType,
    AuditLog,
    AuditAction,
)

# All models must be imported here for Alembic to detect them
__all__ = [
    "Base",
    "BaseModel",
    # Users & Auth
    "User",
    "Role",
    "user_roles",
    "UserStatus",
    # Distributors
    "Distributor",
    "DistributorStatus",
    "Territory",
    "Warehouse",
    "ColdStorageType",
    # Products & Inventory
    "Product",
    "ProductCategory",
    "WarehouseInventory",
    "CartInventory",
    "UpdateSource",
    # Carts & Vendors
    "Cart",
    "CartType",
    "CartStatus",
    "CartLocationHistory",
    "CartPhoto",
    "PhotoAnalysisResult",
    "PhotoProcessingStatus",
    "RefillRequest",
    "RefillRequestSource",
    "RefillRequestStatus",
    "RefillPriority",
    # Orders
    "Order",
    "OrderItem",
    "OrderType",
    "OrderStatus",
    "PaymentStatus",
    # Forecasting & Analytics
    "DemandForecast",
    "ForecastHorizon",
    "ExternalEvent",
    "EventType",
    "WeatherData",
    "CompetitorIntel",
    "CompetitorIntelType",
    "AuditLog",
    "AuditAction",
]
