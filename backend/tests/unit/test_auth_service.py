# =============================================================================
# Jersey Ice Cream Platform — Auth Service Unit Tests
# =============================================================================

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import DuplicateError, InvalidCredentialsError
from app.core.security import hash_password, verify_password
from app.models.user import User, UserStatus
from app.services.auth_service import AuthService


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Password should be hashed with bcrypt."""
        password = "SecurePassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        """Correct password should verify successfully."""
        password = "SecurePassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password should fail verification."""
        hashed = hash_password("CorrectPassword1")
        assert verify_password("WrongPassword1", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Same password should produce different hashes (salt)."""
        password = "SecurePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2
        # Both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestAuthService:
    """Test authentication service."""

    @pytest.fixture
    def auth_service(self):
        return AuthService()

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock(spec=User)
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.phone = "+919876543210"
        user.password_hash = hash_password("ValidPassword1")
        user.full_name = "Test User"
        user.status = UserStatus.ACTIVE
        user.failed_login_attempts = 0
        user.roles = []
        user.role_names = ["vendor"]
        user.avatar_url = None
        user.last_login = None
        user.created_at = "2024-01-01T00:00:00Z"
        return user

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service, mock_db):
        """Registration should fail with duplicate email."""
        from app.schemas.auth import RegisterRequest

        request = RegisterRequest(
            email="existing@example.com",
            password="ValidPassword1",
            full_name="Test User",
        )

        with patch.object(
            auth_service.user_repo, "email_exists", new_callable=AsyncMock, return_value=True
        ):
            with pytest.raises(DuplicateError) as exc_info:
                await auth_service.register(mock_db, request)
            assert "email" in str(exc_info.value.message).lower()

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, auth_service, mock_db):
        """Login with non-existent email should fail."""
        from app.schemas.auth import LoginRequest

        request = LoginRequest(email="nonexistent@example.com", password="Password123")

        with patch.object(
            auth_service.user_repo, "get_by_email", new_callable=AsyncMock, return_value=None
        ):
            with pytest.raises(InvalidCredentialsError):
                await auth_service.login(mock_db, request)

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, auth_service, mock_db, mock_user):
        """Login with wrong password should fail and increment counter."""
        from app.schemas.auth import LoginRequest

        request = LoginRequest(email="test@example.com", password="WrongPassword1")

        with patch.object(
            auth_service.user_repo, "get_by_email", new_callable=AsyncMock, return_value=mock_user
        ), patch.object(
            auth_service.user_repo, "increment_failed_login", new_callable=AsyncMock
        ) as mock_increment:
            with pytest.raises(InvalidCredentialsError):
                await auth_service.login(mock_db, request)
            mock_increment.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_locked_account(self, auth_service, mock_db, mock_user):
        """Login should fail when account is locked due to too many failed attempts."""
        from app.schemas.auth import LoginRequest
        from app.core.exceptions import AuthenticationError

        mock_user.failed_login_attempts = 5
        request = LoginRequest(email="test@example.com", password="ValidPassword1")

        with patch.object(
            auth_service.user_repo, "get_by_email", new_callable=AsyncMock, return_value=mock_user
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_service.login(mock_db, request)
            assert "locked" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_login_suspended_account(self, auth_service, mock_db, mock_user):
        """Login should fail for suspended accounts."""
        from app.schemas.auth import LoginRequest
        from app.core.exceptions import AuthenticationError

        mock_user.status = UserStatus.SUSPENDED
        request = LoginRequest(email="test@example.com", password="ValidPassword1")

        with patch.object(
            auth_service.user_repo, "get_by_email", new_callable=AsyncMock, return_value=mock_user
        ):
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_service.login(mock_db, request)
            assert "suspended" in exc_info.value.message.lower()
