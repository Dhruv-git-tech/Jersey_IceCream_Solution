# =============================================================================
# Jersey Ice Cream Platform — Test Configuration
# =============================================================================

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Role, create_access_token


# ─── Event Loop ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── Mock Database Session ───────────────────────────────────────────────────


@pytest_asyncio.fixture
async def mock_db() -> AsyncMock:
    """Mock database session for unit tests."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


# ─── Auth Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def admin_user_id() -> uuid.UUID:
    """Fixture admin user ID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def vendor_user_id() -> uuid.UUID:
    """Fixture vendor user ID."""
    return uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def admin_token(admin_user_id: uuid.UUID) -> str:
    """Generate a valid admin JWT token."""
    return create_access_token(
        user_id=str(admin_user_id),
        roles=[Role.SUPER_ADMIN.value],
    )


@pytest.fixture
def vendor_token(vendor_user_id: uuid.UUID) -> str:
    """Generate a valid vendor JWT token."""
    return create_access_token(
        user_id=str(vendor_user_id),
        roles=[Role.VENDOR.value],
    )


@pytest.fixture
def distributor_admin_token() -> str:
    """Generate a valid distributor admin JWT token."""
    return create_access_token(
        user_id=str(uuid.UUID("00000000-0000-0000-0000-000000000003")),
        roles=[Role.DISTRIBUTOR_ADMIN.value],
        distributor_id=str(uuid.UUID("00000000-0000-0000-0000-000000000010")),
    )


@pytest.fixture
def auth_headers(admin_token: str) -> dict[str, str]:
    """Auth headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


# ─── Sample Data Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def sample_distributor_data() -> dict:
    """Sample distributor creation data."""
    return {
        "company_name": "Mumbai Ice Cream Traders",
        "legal_name": "Mumbai Ice Cream Traders Pvt Ltd",
        "gstin": "27AAPFU0939F1ZV",
        "pan": "AAPFU0939F",
        "contact_phone": "+919876543210",
        "contact_email": "info@mumbaiice.com",
        "address": "123 Ice Cream Lane, Andheri West",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400058",
        "credit_limit": 500000.0,
        "commission_rate": 12.5,
    }


@pytest.fixture
def sample_territory_data() -> dict:
    """Sample territory creation data."""
    return {
        "name": "Andheri Zone",
        "code": "MUM-AND-01",
        "geohash_prefix": "te7u",
        "population_estimate": 250000,
        "area_sq_km": 15.5,
    }


@pytest.fixture
def sample_warehouse_data() -> dict:
    """Sample warehouse creation data."""
    return {
        "name": "Andheri Cold Storage",
        "address": "45 Industrial Area, MIDC Andheri",
        "capacity_liters": 50000.0,
        "cold_storage_type": "deep_freezer",
        "target_temp_celsius": -20.0,
    }
