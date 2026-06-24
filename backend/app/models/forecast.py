# =============================================================================
# Jersey Ice Cream Platform — Forecast, Event, Competitor, Audit Models
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


# ─── Demand Forecasting ─────────────────────────────────────────────────────


class ForecastHorizon(str, enum.Enum):
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    DAILY = "daily"
    WEEKLY = "weekly"


class DemandForecast(BaseModel):
    """
    Demand prediction output from the forecasting engine.

    Each forecast:
    - Predicts demand for a specific product in a territory
    - Includes confidence interval (lower/upper bounds)
    - Records feature importance for explainability
    - Tracks model version for reproducibility

    Partitioned monthly by generated_at.
    """

    __tablename__ = "demand_forecasts"

    territory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("territories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cart_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    horizon: Mapped[ForecastHorizon] = mapped_column(
        Enum(ForecastHorizon, name="forecast_horizon"),
        nullable=False,
        index=True,
    )
    predicted_demand: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_lower: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_upper: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_level: Mapped[float] = mapped_column(
        Float, default=0.95
    )  # 95% confidence interval

    # Actuals (filled in post-hoc for accuracy tracking)
    actual_demand: Mapped[float | None] = mapped_column(Float, nullable=True)
    mape: Mapped[float | None] = mapped_column(Float, nullable=True)  # Mean Absolute % Error

    # Model metadata
    model_name: Mapped[str] = mapped_column(String(100), default="xgboost-ensemble")
    model_version: Mapped[str] = mapped_column(String(50), default="0.1.0")
    feature_importance: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Mood commerce integration
    mood_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mood_events: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Temporal
    forecast_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<DemandForecast(territory={self.territory_id}, horizon={self.horizon}, demand={self.predicted_demand})>"


# ─── External Events ────────────────────────────────────────────────────────


class EventType(str, enum.Enum):
    CRICKET_MATCH = "cricket_match"
    IPL_MATCH = "ipl_match"
    LOCAL_FESTIVAL = "local_festival"
    NATIONAL_HOLIDAY = "national_holiday"
    SCHOOL_EXAM_RESULT = "school_exam_result"
    SCHOOL_VACATION = "school_vacation"
    WEDDING_SEASON = "wedding_season"
    WEATHER_ALERT = "weather_alert"
    POLITICAL_EVENT = "political_event"
    CONCERT_EVENT = "concert_event"
    SPORTS_EVENT = "sports_event"
    RELIGIOUS_FESTIVAL = "religious_festival"
    OTHER = "other"


class ExternalEvent(BaseModel):
    """
    External event affecting ice cream demand.

    Events are collected from:
    - Weather APIs
    - Cricket/sports APIs
    - Government holiday calendars
    - Local festival databases
    - Manual entry by regional managers

    Each event has a geographic impact area and mood score
    used by the Mood Commerce Engine (Module 5).
    """

    __tablename__ = "external_events"

    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Geographic scope
    location: Mapped[str | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    impact_radius_km: Mapped[float] = mapped_column(Float, default=50.0)
    affected_geohashes: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Impact scoring (for Mood Commerce Engine)
    mood_score: Mapped[float] = mapped_column(
        Float, default=0.0
    )  # -1.0 to 1.0 (negative = demand decrease)
    base_impact: Mapped[float] = mapped_column(Float, default=0.5)
    category_multipliers: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {"cone": 1.3, "premium": 1.5}

    # Temporal
    event_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    event_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_recurring: Mapped[bool] = mapped_column(default=False)
    recurrence_pattern: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Cron expression

    # Source
    source: Mapped[str] = mapped_column(String(100), default="manual")
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_verified: Mapped[bool] = mapped_column(default=False)

    def __repr__(self) -> str:
        return f"<ExternalEvent(type={self.event_type}, title={self.title})>"


# ─── Weather Data ────────────────────────────────────────────────────────────


class WeatherData(BaseModel):
    """
    Weather observations for demand correlation.

    Collected hourly per geohash cell from OpenWeatherMap API.
    Key demand correlations:
    - Temperature > 35°C → +40% demand
    - Rain/storm → -30% demand
    - Humidity > 80% → slight demand increase (need for cooling)

    Partitioned weekly by recorded_at.
    """

    __tablename__ = "weather_data"

    geohash: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # Temperature
    temperature_celsius: Mapped[float] = mapped_column(Float, nullable=False)
    feels_like_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    heat_index: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Conditions
    humidity_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[float] = mapped_column(Float, default=0.0)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    uv_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    condition: Mapped[str] = mapped_column(
        String(50), default="clear"
    )  # clear, cloudy, rain, storm, etc.
    condition_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Forecast vs Actual
    is_forecast: Mapped[bool] = mapped_column(default=False)
    forecast_hours_ahead: Mapped[int | None] = mapped_column(Integer, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), default="openweathermap")

    def __repr__(self) -> str:
        return f"<WeatherData(geohash={self.geohash}, temp={self.temperature_celsius}°C)>"


# ─── Competitor Intelligence ────────────────────────────────────────────────


class CompetitorIntelType(str, enum.Enum):
    PRICE_CHANGE = "price_change"
    PROMOTION = "promotion"
    NEW_PRODUCT = "new_product"
    DISTRIBUTION_EXPANSION = "distribution_expansion"
    SOCIAL_MENTION = "social_mention"
    NEWS_ARTICLE = "news_article"
    FIELD_REPORT = "field_report"


class CompetitorIntel(BaseModel):
    """
    Competitor intelligence data point.

    Collected from:
    - Public social media APIs (Twitter/X, Instagram)
    - News aggregation (Google Alerts)
    - Competitor websites (pricing, product launches)
    - Field reports from distributors/vendors

    Relevance scoring uses TF-IDF cosine similarity against
    known competitor keywords. Threshold: 0.4
    """

    __tablename__ = "competitor_intel"

    competitor_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # Amul, Heritage, Arun, Vadilal, Mother Dairy
    intel_type: Mapped[CompetitorIntelType] = mapped_column(
        Enum(CompetitorIntelType, name="competitor_intel_type"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_platform: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Structured data for specific intel types
    structured_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # For price changes: {"product": "...", "old_price": 10, "new_price": 15}
    # For promotions: {"discount": "20%", "valid_until": "...", "products": [...]}

    # Scoring
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # -1.0 to 1.0
    impact_assessment: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # low, medium, high

    # Location scope
    affected_regions: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    verified: Mapped[bool] = mapped_column(default=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<CompetitorIntel(competitor={self.competitor_name}, type={self.intel_type})>"


# ─── Audit Log ──────────────────────────────────────────────────────────────


class AuditAction(str, enum.Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    APPROVE = "approve"
    REJECT = "reject"


class AuditLog(BaseModel):
    """
    Immutable audit trail for compliance and security.

    Every significant operation is logged:
    - CRUD operations on business entities
    - Authentication events (login, logout, failed attempts)
    - Data exports and imports
    - Approval/rejection workflows

    Partitioned monthly by created_at.
    Retained for 5 years per compliance requirements.

    Design:
    - Soft delete is DISABLED for audit logs (immutable)
    - old_values/new_values capture the full diff
    - IP address and user agent for security forensics
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # "distributor", "cart", "order", etc.
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action"),
        nullable=False,
        index=True,
    )

    # Change tracking
    old_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changes_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Additional context
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog(user={self.user_id}, action={self.action}, entity={self.entity_type})>"
