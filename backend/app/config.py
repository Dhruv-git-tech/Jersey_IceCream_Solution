# =============================================================================
# Jersey Ice Cream Platform — Application Configuration
# =============================================================================
# Centralized configuration using pydantic-settings.
# All values are loaded from environment variables with validation.
# =============================================================================

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Design Decision:
        Using pydantic-settings ensures type-safe configuration with validation
        at startup. Fails fast if required config is missing rather than at
        runtime when a feature is first used.

    All secrets should come from environment variables (injected via Docker,
    K8s secrets, or Vault). Never hardcode secrets.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ─────────────────────────────────────────────────────
    app_name: str = "Jersey Ice Cream Platform"
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = False
    app_version: str = "0.1.0"
    app_host: str = "0.0.0.0"  # noqa: S104
    app_port: int = 8000
    app_workers: int = 4

    # ─── Security ────────────────────────────────────────────────────────
    secret_key: Annotated[str, Field(min_length=32)] = (
        "dev-secret-key-change-in-production-must-be-64-chars-long-minimum"
    )
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:3000"

    # ─── PostgreSQL ──────────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://jersey:jersey_secure_password_change_me@localhost:5432/jersey_platform"
    )
    database_url_sync: str = (
        "postgresql+psycopg2://jersey:jersey_secure_password_change_me@localhost:5432/jersey_platform"
    )
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_echo: bool = False

    # ─── Redis ───────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    redis_socket_timeout: int = 5
    redis_retry_on_timeout: bool = True

    # ─── Kafka ───────────────────────────────────────────────────────────
    kafka_bootstrap_servers: str = "localhost:9094"
    kafka_group_id: str = "jersey-platform"
    kafka_auto_offset_reset: str = "earliest"
    kafka_enable_auto_commit: bool = False
    kafka_max_poll_records: int = 500

    # ─── MinIO ───────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_use_ssl: bool = False
    minio_bucket_cart_photos: str = "cart-photos"
    minio_bucket_model_artifacts: str = "model-artifacts"

    # ─── External APIs ───────────────────────────────────────────────────
    weather_api_key: str = ""
    weather_api_base_url: str = "https://api.openweathermap.org/data/2.5"
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""

    # ─── AI / ML ─────────────────────────────────────────────────────────
    yolo_model_path: str = "./ai/models/yolo/weights/best.pt"
    yolo_confidence_threshold: float = 0.6
    forecast_model_path: str = "./ai/models/forecasting/weights/"

    # ─── Observability ───────────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "jersey-backend"
    log_level: str = "INFO"
    prometheus_port: int = 9090

    # ─── Rate Limiting ───────────────────────────────────────────────────
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst: int = 10

    # ─── Derived Properties ──────────────────────────────────────────────
    @property
    def is_development(self) -> bool:
        return self.app_env == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.app_env == Environment.TESTING

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info: object) -> str:
        """Ensure secret key is sufficiently strong in production."""
        # We access the data dict directly since info.data may not have app_env yet
        # Production validation happens at startup via explicit check
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached application settings.

    Uses lru_cache to ensure settings are only loaded once from environment.
    Thread-safe due to Python's GIL and lru_cache implementation.
    """
    return Settings()
