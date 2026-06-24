# =============================================================================
# Jersey Ice Cream Platform — FastAPI Application Entrypoint
# =============================================================================
# Main application factory with lifecycle management, middleware registration,
# and exception handlers.
#
# Design Decision:
#   Using FastAPI's lifespan context manager (not deprecated on_event)
#   for proper async resource lifecycle.
#   All startup/shutdown operations are centralized here.
# =============================================================================

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.config import get_settings
from app.core.exceptions import JerseyBaseError

settings = get_settings()

# ─── Structured Logging ─────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer() if settings.is_production else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level)
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


# ─── Application Lifespan ───────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.

    Startup:
    1. Initialize database connection pool
    2. Initialize Redis connection pool
    3. Initialize Kafka producer
    4. Initialize MinIO buckets
    5. Set up Prometheus metrics

    Shutdown:
    1. Close Kafka producer (flush pending messages)
    2. Close Redis connections
    3. Dispose database engine
    """
    logger.info(
        "Starting Jersey Ice Cream Platform",
        version=settings.app_version,
        environment=settings.app_env.value,
    )

    # ─── Startup ────────────────────────────────────────────────────
    try:
        # Database
        from app.database import init_db

        await init_db()
        logger.info("Database initialized")
    except Exception:
        logger.error("Database initialization failed", exc_info=True)

    try:
        # Redis
        from app.core.cache import get_redis_client

        await get_redis_client()
        logger.info("Redis initialized")
    except Exception:
        logger.warning("Redis initialization failed — caching disabled", exc_info=True)

    try:
        # Kafka
        from app.core.events import get_event_producer

        await get_event_producer()
        logger.info("Kafka producer initialized")
    except Exception:
        logger.warning("Kafka initialization failed — events will be logged", exc_info=True)

    try:
        # MinIO
        from app.core.storage import get_object_storage

        storage = get_object_storage()
        await storage.initialize()
        logger.info("MinIO initialized")
    except Exception:
        logger.warning("MinIO initialization failed — file uploads disabled", exc_info=True)

    # Prometheus
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            should_respect_env_var=False,
            excluded_handlers=["/health", "/health/live", "/health/ready", "/metrics"],
            inprogress_name="jersey_inprogress_requests",
            inprogress_labels=True,
        ).instrument(app).expose(app, include_in_schema=False, should_gzip=True)
        logger.info("Prometheus metrics enabled")
    except Exception:
        logger.warning("Prometheus initialization failed", exc_info=True)

    logger.info("Application startup complete")

    yield

    # ─── Shutdown ───────────────────────────────────────────────────
    logger.info("Shutting down...")

    try:
        from app.core.events import close_event_producer

        await close_event_producer()
    except Exception:
        pass

    try:
        from app.core.cache import close_redis

        await close_redis()
    except Exception:
        pass

    try:
        from app.database import close_db

        await close_db()
    except Exception:
        pass

    logger.info("Shutdown complete")


# ─── Application Factory ────────────────────────────────────────────────────


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Jersey Ice Cream Demand Intelligence Platform",
        description=(
            "AI-Powered platform for hyperlocal ice cream demand prediction "
            "and stock movement optimization across 10,000+ push carts."
        ),
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ─── CORS ───────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
    )

    # ─── Request Logging Middleware ─────────────────────────────────
    @application.middleware("http")
    async def logging_middleware(request: Request, call_next) -> Response:
        """Log all requests with timing and request ID."""
        import uuid

        request_id = str(uuid.uuid4())[:8]
        start_time = time.monotonic()

        # Bind request context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(duration_ms)

        logger.info(
            "Request completed",
            status=response.status_code,
            duration_ms=duration_ms,
            client=request.client.host if request.client else "unknown",
        )

        return response

    # ─── Exception Handlers ─────────────────────────────────────────

    @application.exception_handler(JerseyBaseError)
    async def jersey_exception_handler(request: Request, exc: JerseyBaseError) -> ORJSONResponse:
        """Handle all custom application exceptions."""
        logger.warning(
            "Application error",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
        )
        return ORJSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        """Handle Pydantic validation errors with consistent format."""
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )
        return ORJSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"errors": errors},
                }
            },
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> ORJSONResponse:
        """Handle standard HTTP exceptions."""
        return ORJSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                }
            },
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> ORJSONResponse:
        """Catch-all for unhandled exceptions. Log full stack trace."""
        logger.error("Unhandled exception", exc_info=True)
        return ORJSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred"
                    if settings.is_production
                    else str(exc),
                }
            },
        )

    # ─── Register Routers ──────────────────────────────────────────
    application.include_router(health_router)
    application.include_router(v1_router)

    return application


# ─── Application Instance ───────────────────────────────────────────────────

app = create_application()
