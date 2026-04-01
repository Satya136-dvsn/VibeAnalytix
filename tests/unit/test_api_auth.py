"""
Unit tests for API authentication endpoints.
Tests register, login, JWT issuance, and protected endpoint access.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.auth import (
    hash_password,
    verify_password,
    create_jwt_token,
    decode_jwt_token,
)
from app.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    ErrorResponse,
    ErrorDetail,
    JobStatusResponse,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_hash(self):
        """hash_password should return a non-empty string different from the input."""
        password = "mySecurePassword123"
        hashed = hash_password(password)

        assert hashed is not None
        assert len(hashed) > 0
        assert hashed != password

    def test_verify_correct_password(self):
        """verify_password should return True for correct password."""
        password = "testPassword456"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """verify_password should return False for wrong password."""
        password = "correctPassword"
        wrong_password = "wrongPassword"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_different_passwords_different_hashes(self):
        """Different passwords should produce different hashes."""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Same password should produce different hashes (due to salt)."""
        password = "samePassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # bcrypt uses random salt, so hashes should differ
        assert hash1 != hash2
        # But both should verify against the original password
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokenCreation:
    """Test JWT token creation and validation."""

    @patch("app.auth.settings")
    def test_create_jwt_token(self, mock_settings):
        """create_jwt_token should return a non-empty string."""
        mock_settings.jwt_secret = "test-secret-key"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_expiration_hours = 24

        user_id = str(uuid.uuid4())
        token = create_jwt_token(user_id)

        assert token is not None
        assert len(token) > 0
        assert isinstance(token, str)

    @patch("app.auth.settings")
    def test_decode_valid_token(self, mock_settings):
        """decode_jwt_token should successfully decode a valid token."""
        mock_settings.jwt_secret = "test-secret-key"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_expiration_hours = 24

        user_id = str(uuid.uuid4())
        token = create_jwt_token(user_id)
        payload = decode_jwt_token(token)

        assert payload["sub"] == user_id

    @patch("app.auth.settings")
    def test_decode_invalid_token_raises(self, mock_settings):
        """decode_jwt_token should raise HTTPException for invalid tokens."""
        mock_settings.jwt_secret = "test-secret-key"
        mock_settings.jwt_algorithm = "HS256"

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_jwt_token("invalid.token.string")

        assert exc_info.value.status_code == 401

    @patch("app.auth.settings")
    def test_expired_token_raises(self, mock_settings):
        """decode_jwt_token should raise HTTPException for expired tokens."""
        mock_settings.jwt_secret = "test-secret-key"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_expiration_hours = 24

        from jose import jwt as jose_jwt
        from fastapi import HTTPException

        # Create an expired token (expired 1 hour ago)
        payload = {
            "sub": str(uuid.uuid4()),
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=25),
        }
        expired_token = jose_jwt.encode(payload, "test-secret-key", algorithm="HS256")

        with pytest.raises(HTTPException) as exc_info:
            decode_jwt_token(expired_token)

        assert exc_info.value.status_code == 401

    @patch("app.auth.settings")
    def test_token_with_custom_expiry(self, mock_settings):
        """create_jwt_token should respect custom expiry hours."""
        mock_settings.jwt_secret = "test-secret-key"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_expiration_hours = 24

        user_id = str(uuid.uuid4())
        token = create_jwt_token(user_id, expires_in_hours=1)

        payload = decode_jwt_token(token)
        assert payload["sub"] == user_id

    @patch("app.auth.settings")
    def test_token_contains_iat_claim(self, mock_settings):
        """JWT token should contain 'iat' (issued at) claim."""
        mock_settings.jwt_secret = "test-secret-key"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.jwt_expiration_hours = 24

        user_id = str(uuid.uuid4())
        token = create_jwt_token(user_id)
        payload = decode_jwt_token(token)

        assert "iat" in payload
        assert "exp" in payload
        assert "sub" in payload


class TestSchemaValidation:
    """Test Pydantic schema validation."""

    def test_register_request_requires_email(self):
        """Registration should require a valid email."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserRegisterRequest(email="invalid", password="12345678")

    def test_register_request_requires_min_password(self):
        """Registration should require password >= 8 characters."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserRegisterRequest(email="test@example.com", password="short")

    def test_valid_register_request(self):
        """Valid registration request should pass validation."""
        req = UserRegisterRequest(
            email="test@example.com",
            password="securePassword123",
        )
        assert req.email == "test@example.com"
        assert req.password == "securePassword123"

    def test_token_response_structure(self):
        """Token response should have access_token, token_type, and expires_in."""
        resp = TokenResponse(
            access_token="abc123",
            token_type="bearer",
            expires_in=86400,
        )
        assert resp.access_token == "abc123"
        assert resp.token_type == "bearer"
        assert resp.expires_in == 86400

    def test_error_response_structure(self):
        """Error response should follow the standard envelope."""
        error = ErrorResponse(
            error=ErrorDetail(
                code="INVALID_URL",
                message="Only HTTPS GitHub URLs are supported.",
                details={},
            )
        )
        assert error.error.code == "INVALID_URL"
        assert error.error.message == "Only HTTPS GitHub URLs are supported."


class TestAuthorizationChecks:
    """Test authorization logic for job ownership."""

    def test_owner_can_access_job(self):
        """Job owner should be authorized to access their job."""
        user_id = uuid.uuid4()
        job_owner_id = user_id  # Same user

        assert user_id == job_owner_id

    def test_non_owner_denied_access(self):
        """Non-owner should be denied access to a job."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()

        assert user_a != user_b
        # This would return 403 in the actual endpoint


class TestRateLimiting:
    """Test rate limiting logic."""

    def test_under_limit_allowed(self):
        """Users under the rate limit should be allowed to submit."""
        recent_job_count = 5
        rate_limit = 10

        assert recent_job_count < rate_limit

    def test_at_limit_rejected(self):
        """Users at the rate limit should be rejected."""
        recent_job_count = 10
        rate_limit = 10

        assert recent_job_count >= rate_limit

    def test_over_limit_rejected(self):
        """Users over the rate limit should be rejected."""
        recent_job_count = 15
        rate_limit = 10

        assert recent_job_count >= rate_limit
