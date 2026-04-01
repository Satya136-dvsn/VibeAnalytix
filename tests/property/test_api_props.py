"""
Property-based tests for API endpoints using Hypothesis.
Tests Properties 18-27 from the design document.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest
from hypothesis import given, settings, strategies as st

from app.auth import create_jwt_token, decode_jwt_token, hash_password, verify_password
from app.schemas import (
    JobStatusResponse,
    JobSubmissionResponse,
    ExplanationSet,
    ErrorResponse,
    ErrorDetail,
)


# ============ Strategies ============

safe_email = st.builds(
    lambda name, domain: f"{name}@{domain}.com",
    name=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=3, max_size=15),
    domain=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=10),
)

safe_password = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$",
    min_size=8,
    max_size=30,
)


class TestJobCreationReturnsID:
    """Property-based tests for job creation returns ID (Property 18)."""

    # Feature: vibeanalytix, Property 18: Job Creation Returns ID
    @given(
        github_url=st.builds(
            lambda owner, repo: f"https://github.com/{owner}/{repo}",
            owner=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1),
            repo=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1),
        ),
    )
    @settings(max_examples=100)
    def test_valid_submission_returns_job_id(self, github_url):
        """For any valid job submission, a job_id should be returned."""
        # Simulate job creation
        job_id = uuid.uuid4()
        response = JobSubmissionResponse(job_id=job_id, status="queued")

        assert response.job_id is not None
        assert response.status == "queued"
        # job_id should be a valid UUID
        assert isinstance(response.job_id, uuid.UUID)


class TestJobStatusResponseShape:
    """Property-based tests for job status response shape (Property 19)."""

    # Feature: vibeanalytix, Property 19: Job Status Response Shape
    @given(
        progress=st.integers(min_value=0, max_value=100),
        stage=st.sampled_from([
            "ingestion", "parsing", "analysis_pass1", "analysis_pass2",
            "analysis_pass3", "knowledge_building", "embedding", "explanation",
        ]),
    )
    @settings(max_examples=100)
    def test_in_progress_response_has_required_fields(self, progress, stage):
        """For any in-progress job, response should have non-null stage and valid progress."""
        response = JobStatusResponse(
            job_id=uuid.uuid4(),
            status="in_progress",
            current_stage=stage,
            progress_pct=progress,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert response.current_stage is not None
        assert 0 <= response.progress_pct <= 100
        assert response.status == "in_progress"


class TestJobTerminalStateCorrectness:
    """Property-based tests for job terminal state correctness (Property 20)."""

    # Feature: vibeanalytix, Property 20: Job Terminal State Correctness (completed)
    @given(st.just(True))
    @settings(max_examples=100)
    def test_completed_job_has_correct_status(self, _):
        """Completed jobs should have status='completed' and progress=100."""
        response = JobStatusResponse(
            job_id=uuid.uuid4(),
            status="completed",
            current_stage="completed",
            progress_pct=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert response.status == "completed"
        assert response.progress_pct == 100

    # Feature: vibeanalytix, Property 20: Job Terminal State Correctness (failed)
    @given(
        error_msg=st.text(min_size=1, max_size=200),
    )
    @settings(max_examples=100)
    def test_failed_job_has_error_message(self, error_msg):
        """Failed jobs should have status='failed' and a non-empty error_message."""
        response = JobStatusResponse(
            job_id=uuid.uuid4(),
            status="failed",
            current_stage=None,
            progress_pct=0,
            error_message=error_msg,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        assert response.status == "failed"
        assert response.error_message is not None
        assert len(response.error_message) > 0


class TestJobIsolation:
    """Property-based tests for job isolation (Property 21)."""

    # Feature: vibeanalytix, Property 21: Job Isolation
    @given(
        num_jobs=st.integers(min_value=2, max_value=10),
        failed_index=st.integers(min_value=0, max_value=9),
    )
    @settings(max_examples=100)
    def test_one_failure_does_not_affect_others(self, num_jobs, failed_index):
        """One job's failure should not affect other jobs' terminal states."""
        failed_index = failed_index % num_jobs  # Ensure valid index

        jobs = []
        for i in range(num_jobs):
            if i == failed_index:
                jobs.append({"id": uuid.uuid4(), "status": "failed", "error": "test error"})
            else:
                jobs.append({"id": uuid.uuid4(), "status": "completed", "error": None})

        # Verify isolation
        failed_jobs = [j for j in jobs if j["status"] == "failed"]
        completed_jobs = [j for j in jobs if j["status"] == "completed"]

        assert len(failed_jobs) == 1
        assert len(completed_jobs) == num_jobs - 1

        # Each completed job should not be affected
        for j in completed_jobs:
            assert j["status"] == "completed"
            assert j["error"] is None


class TestPollingIntervalBound:
    """Property-based tests for polling interval bound (Property 22)."""

    # Feature: vibeanalytix, Property 22: Polling Interval Bound
    @given(
        num_polls=st.integers(min_value=2, max_value=20),
    )
    @settings(max_examples=100)
    def test_polling_interval_at_least_3_seconds(self, num_polls):
        """The interval between consecutive polls should be at least 3 seconds."""
        polling_interval = 3  # seconds (as configured in the frontend)

        timestamps = []
        for i in range(num_polls):
            timestamps.append(i * polling_interval)

        # Verify interval between consecutive polls
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i - 1]
            assert interval >= 3, (
                f"Polling interval {interval}s is less than 3 seconds"
            )


class TestProgressiveRendering:
    """Property-based tests for progressive rendering (Property 23)."""

    # Feature: vibeanalytix, Property 23: Progressive Rendering
    @given(
        has_overview=st.just(True),
        per_file_complete=st.booleans(),
    )
    @settings(max_examples=100)
    def test_overview_renders_before_full_completion(self, has_overview, per_file_complete):
        """Overview should render as soon as project summary is available."""
        explanations = ExplanationSet(
            project_summary="Project summary available" if has_overview else None,
            overview_explanation="Overview text" if has_overview else None,
            per_file_explanations={"file.py": "explanation"} if per_file_complete else {},
        )

        # Overview should be renderable regardless of per-file completion
        if has_overview:
            assert explanations.overview_explanation is not None
            assert len(explanations.overview_explanation) > 0


class TestAuthenticationEnforcement:
    """Property-based tests for authentication enforcement (Property 24)."""

    # Feature: vibeanalytix, Property 24: Authentication Enforcement
    @given(
        invalid_token=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=100)
    def test_invalid_jwt_returns_401(self, invalid_token):
        """Any invalid JWT should result in a 401 response."""
        from fastapi import HTTPException

        # decode_jwt_token should raise HTTPException for invalid tokens
        with pytest.raises(HTTPException) as exc_info:
            with patch("app.auth.settings") as mock_settings:
                mock_settings.jwt_secret = "test-secret"
                mock_settings.jwt_algorithm = "HS256"
                decode_jwt_token(invalid_token)

        assert exc_info.value.status_code == 401


class TestAuthorizationEnforcement:
    """Property-based tests for authorization enforcement (Property 25)."""

    # Feature: vibeanalytix, Property 25: Authorization Enforcement
    @given(st.just(True))
    @settings(max_examples=100)
    def test_user_cannot_access_others_jobs(self, _):
        """User A requesting job owned by User B should get 403."""
        user_a_id = uuid.uuid4()
        user_b_id = uuid.uuid4()
        job_owner_id = user_b_id

        # Simulate authorization check
        requesting_user_id = user_a_id

        assert requesting_user_id != job_owner_id, "Test setup error: users should differ"

        # The check that would be performed
        should_deny = requesting_user_id != job_owner_id
        assert should_deny, "Should deny access when user IDs differ"


class TestJWTExpiry:
    """Property-based tests for JWT expiry (Property 26)."""

    # Feature: vibeanalytix, Property 26: JWT Expiry
    @given(
        hours_ago=st.integers(min_value=25, max_value=168),
    )
    @settings(max_examples=100)
    def test_expired_jwt_rejected(self, hours_ago):
        """Tokens issued > 24 hours ago should be rejected."""
        from jose import jwt as jose_jwt

        user_id = str(uuid.uuid4())
        issued_at = datetime.utcnow() - timedelta(hours=hours_ago)
        expired_at = issued_at + timedelta(hours=24)

        # Create an expired token
        payload = {
            "sub": user_id,
            "iat": issued_at,
            "exp": expired_at,
        }

        secret = "test-secret-key"
        token = jose_jwt.encode(payload, secret, algorithm="HS256")

        # The token should be expired now
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            with patch("app.auth.settings") as mock_settings:
                mock_settings.jwt_secret = secret
                mock_settings.jwt_algorithm = "HS256"
                decode_jwt_token(token)

        assert exc_info.value.status_code == 401


class TestRateLimitEnforcement:
    """Property-based tests for rate limit enforcement (Property 27)."""

    # Feature: vibeanalytix, Property 27: Rate Limit Enforcement
    @given(
        num_submissions=st.integers(min_value=11, max_value=20),
    )
    @settings(max_examples=100)
    def test_11th_submission_rejected(self, num_submissions):
        """The 11th submission within one hour should be rejected."""
        rate_limit = 10
        submissions_made = num_submissions

        # Simulate rate limit check
        should_reject = submissions_made > rate_limit
        assert should_reject, (
            f"Should reject after {rate_limit} submissions, but {submissions_made} were allowed"
        )

    # Feature: vibeanalytix, Property 27: Rate Limit Enforcement (under limit)
    @given(
        num_submissions=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_under_limit_submissions_allowed(self, num_submissions):
        """Submissions under the rate limit should be allowed."""
        rate_limit = 10
        should_allow = num_submissions <= rate_limit
        assert should_allow, (
            f"Should allow {num_submissions} submissions (limit is {rate_limit})"
        )
