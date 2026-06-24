# =============================================================================
# Jersey Ice Cream Platform — V1 API Router
# =============================================================================

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.distributors import router as distributors_router

router = APIRouter(prefix="/api/v1")

# Include module routers
router.include_router(auth_router)
router.include_router(distributors_router)

# Future module routers will be added here:
# router.include_router(carts_router)
# router.include_router(inventory_router)
# router.include_router(forecasts_router)
# router.include_router(vision_router)
# router.include_router(mood_router)
# router.include_router(swarm_router)
# router.include_router(competitors_router)
# router.include_router(command_center_router)
# router.include_router(webhooks_router)
