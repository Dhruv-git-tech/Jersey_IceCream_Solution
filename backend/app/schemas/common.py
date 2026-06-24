# =============================================================================
# Jersey Ice Cream Platform — Common Pydantic Schemas
# =============================================================================
# Shared request/response schemas used across all modules.
# =============================================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ─── Base Response Schemas ───────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str
    services: dict[str, Any] = {}


class ErrorDetail(BaseModel):
    """Error detail in API response."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: ErrorDetail


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    details: dict[str, Any] | None = None


# ─── Pagination ──────────────────────────────────────────────────────────────


class PaginationParams(BaseModel):
    """
    Pagination query parameters.

    Uses cursor-based pagination for stable ordering with large datasets.
    Offset pagination available for simpler use cases.

    DSA: Cursor-based pagination is O(log n) with indexed cursor column
    vs O(n) for OFFSET which must skip rows.
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Number of items per page"
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginationMeta(BaseModel):
    """Pagination metadata in list responses."""

    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.

    Usage:
        PaginatedResponse[DistributorResponse](items=[...], pagination=...)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[T]
    pagination: PaginationMeta


# ─── Sorting & Filtering ────────────────────────────────────────────────────


class SortOrder(BaseModel):
    """Sort order specification."""

    field: str = "created_at"
    direction: str = Field(default="desc", pattern="^(asc|desc)$")


class DateRangeFilter(BaseModel):
    """Date range filter for time-based queries."""

    start_date: datetime | None = None
    end_date: datetime | None = None


# ─── Audit Fields ────────────────────────────────────────────────────────────


class AuditMixin(BaseModel):
    """Common audit fields included in all entity responses."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ─── Geo Types ───────────────────────────────────────────────────────────────


class GeoPoint(BaseModel):
    """Geographic point (latitude, longitude)."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class GeoBoundingBox(BaseModel):
    """Geographic bounding box for spatial queries."""

    north_east: GeoPoint
    south_west: GeoPoint
