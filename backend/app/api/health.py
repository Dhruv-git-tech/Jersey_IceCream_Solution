# =============================================================================
# Jersey Ice Cream Platform — Health Check API
# =============================================================================

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.database import check_db_health
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns application health status and service connectivity.",
)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check.

    Used by:
    - Kubernetes liveness/readiness probes
    - Load balancer health checks
    - Monitoring systems
    """
    services: dict = {}

    # Check database
    db_health = await check_db_health()
    services["database"] = db_health

    # Check Redis
    try:
        from app.core.cache import check_redis_health

        redis_health = await check_redis_health()
        services["redis"] = redis_health
    except Exception as e:
        services["redis"] = {"status": "unhealthy", "error": str(e)}

    # Check MinIO
    try:
        from app.core.storage import check_storage_health

        storage_health = await check_storage_health()
        services["storage"] = storage_health
    except Exception as e:
        services["storage"] = {"status": "unhealthy", "error": str(e)}

    # Overall status: healthy only if critical services are up
    critical_healthy = (
        services.get("database", {}).get("status") == "healthy"
    )
    overall_status = "healthy" if critical_healthy else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.app_env.value,
        services=services,
    )


@router.get(
    "/health/live",
    summary="Liveness probe",
    description="Simple liveness probe for Kubernetes.",
)
async def liveness() -> dict:
    """Minimal liveness check — returns 200 if process is alive."""
    return {"status": "alive"}


@router.get(
    "/health/ready",
    summary="Readiness probe",
    description="Readiness probe — checks if the application can serve traffic.",
)
async def readiness() -> dict:
    """
    Readiness check — verifies database connectivity.

    If this fails, Kubernetes stops routing traffic to this pod.
    """
    db_health = await check_db_health()
    if db_health["status"] != "healthy":
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Database not ready")
    return {"status": "ready"}
