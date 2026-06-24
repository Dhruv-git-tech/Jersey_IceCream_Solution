# =============================================================================
# Jersey Ice Cream Platform — Custom Exception Hierarchy
# =============================================================================
# Structured exception hierarchy for consistent error handling across the
# application. Each exception maps to an HTTP status code and error code
# for API responses.
#
# Design Decision:
#   Custom exceptions over generic HTTPException because:
#   1. Business logic layer shouldn't know about HTTP
#   2. Consistent error response format across all endpoints
#   3. Exception handlers can add logging, metrics, and tracing
#   4. Easier to test service layer in isolation
# =============================================================================

from __future__ import annotations

from typing import Any


class JerseyBaseError(Exception):
    """
    Base exception for all application errors.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error code for client consumption
        status_code: HTTP status code for API response
        details: Optional additional error context
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize exception to API response format."""
        response = {
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }
        if self.details:
            response["error"]["details"] = self.details
        return response


# ─── Authentication & Authorization ─────────────────────────────────────────


class AuthenticationError(JerseyBaseError):
    """Raised when authentication fails (invalid credentials, expired token)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTH_FAILED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid email/password combination."""

    def __init__(self) -> None:
        super().__init__(
            message="Invalid email or password",
            error_code="INVALID_CREDENTIALS",
        )


class TokenExpiredError(AuthenticationError):
    """JWT token has expired."""

    def __init__(self) -> None:
        super().__init__(
            message="Token has expired",
            error_code="TOKEN_EXPIRED",
        )


class TokenInvalidError(AuthenticationError):
    """JWT token is malformed or has invalid signature."""

    def __init__(self) -> None:
        super().__init__(
            message="Invalid token",
            error_code="TOKEN_INVALID",
        )


class TokenBlacklistedError(AuthenticationError):
    """JWT token has been revoked."""

    def __init__(self) -> None:
        super().__init__(
            message="Token has been revoked",
            error_code="TOKEN_REVOKED",
        )


class InsufficientPermissionsError(JerseyBaseError):
    """User lacks required permissions for the operation."""

    def __init__(
        self,
        required_permission: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        msg = "Insufficient permissions"
        if required_permission:
            msg = f"Insufficient permissions: requires '{required_permission}'"
        super().__init__(
            message=msg,
            error_code="INSUFFICIENT_PERMISSIONS",
            status_code=403,
            details=details,
        )


# ─── Resource Errors ────────────────────────────────────────────────────────


class NotFoundError(JerseyBaseError):
    """Requested resource does not exist."""

    def __init__(
        self,
        resource_type: str = "Resource",
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        msg = f"{resource_type} not found"
        if resource_id:
            msg = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(
            message=msg,
            error_code=f"{resource_type.upper()}_NOT_FOUND",
            status_code=404,
            details=details,
        )


class ConflictError(JerseyBaseError):
    """Resource already exists or state conflict."""

    def __init__(
        self,
        message: str = "Resource conflict",
        error_code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=409,
            details=details,
        )


class DuplicateError(ConflictError):
    """Duplicate resource creation attempt."""

    def __init__(
        self,
        resource_type: str = "Resource",
        field: str = "id",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=f"{resource_type} with this {field} already exists",
            error_code=f"{resource_type.upper()}_DUPLICATE",
            details=details,
        )


# ─── Validation Errors ──────────────────────────────────────────────────────


class ValidationError(JerseyBaseError):
    """Input validation failed."""

    def __init__(
        self,
        message: str = "Validation error",
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=422,
            details=details,
        )


class BusinessRuleError(JerseyBaseError):
    """Business logic constraint violated."""

    def __init__(
        self,
        message: str = "Business rule violation",
        error_code: str = "BUSINESS_RULE_VIOLATION",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=422,
            details=details,
        )


# ─── Rate Limiting ──────────────────────────────────────────────────────────


class RateLimitExceededError(JerseyBaseError):
    """API rate limit exceeded."""

    def __init__(
        self,
        retry_after_seconds: int = 60,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={"retry_after_seconds": retry_after_seconds, **(details or {})},
        )


# ─── External Service Errors ────────────────────────────────────────────────


class ExternalServiceError(JerseyBaseError):
    """External service (Weather API, WhatsApp, etc.) is unavailable."""

    def __init__(
        self,
        service_name: str = "External service",
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message or f"{service_name} is currently unavailable",
            error_code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            details={"service": service_name, **(details or {})},
        )


class StorageError(ExternalServiceError):
    """Object storage (MinIO) operation failed."""

    def __init__(
        self,
        operation: str = "unknown",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            service_name="Object Storage",
            message=f"Storage operation '{operation}' failed",
            details=details,
        )


class QueueError(ExternalServiceError):
    """Message queue (Kafka) operation failed."""

    def __init__(
        self,
        operation: str = "unknown",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            service_name="Message Queue",
            message=f"Queue operation '{operation}' failed",
            details=details,
        )
