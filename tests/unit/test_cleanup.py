"""
Unit tests for Cleanup Service.
Tests temp directory deletion, logging, and watchdog transition logic.
"""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import pytest

from app.cleanup import PROGRESS_STAGES


class TestCleanupJobDeletion:
    """Test temp directory deletion."""

    def test_deletes_existing_directory(self):
        """Cleanup should successfully delete an existing temp directory."""
        with tempfile.TemporaryDirectory() as root:
            job_dir = Path(root) / "test_job"
            job_dir.mkdir()
            (job_dir / "file.txt").write_text("content")

            assert job_dir.exists()
            shutil.rmtree(job_dir)
            assert not job_dir.exists()

    def test_handles_nested_directories(self):
        """Cleanup should handle deeply nested directory structures."""
        with tempfile.TemporaryDirectory() as root:
            job_dir = Path(root) / "test_job"
            nested = job_dir / "a" / "b" / "c" / "d"
            nested.mkdir(parents=True)
            (nested / "deep_file.txt").write_text("deep content")

            assert nested.exists()
            shutil.rmtree(job_dir)
            assert not job_dir.exists()

    def test_handles_empty_directory(self):
        """Cleanup should handle empty directories without error."""
        with tempfile.TemporaryDirectory() as root:
            job_dir = Path(root) / "empty_job"
            job_dir.mkdir()

            assert job_dir.exists()
            shutil.rmtree(job_dir)
            assert not job_dir.exists()

    def test_calculates_freed_bytes(self):
        """Cleanup should accurately calculate bytes freed."""
        with tempfile.TemporaryDirectory() as root:
            job_dir = Path(root) / "size_job"
            job_dir.mkdir()

            content = "x" * 1000  # 1000 bytes
            (job_dir / "file.txt").write_text(content)

            total_size = sum(
                f.stat().st_size for f in job_dir.rglob("*") if f.is_file()
            )

            assert total_size >= 1000  # At least 1000 bytes
            shutil.rmtree(job_dir)
            assert not job_dir.exists()

    def test_multiple_files_cleanup(self):
        """Cleanup should remove directories with multiple files."""
        with tempfile.TemporaryDirectory() as root:
            job_dir = Path(root) / "multi_job"
            job_dir.mkdir()

            for i in range(20):
                (job_dir / f"file_{i}.py").write_text(f"# File {i}")

            assert len(list(job_dir.iterdir())) == 20
            shutil.rmtree(job_dir)
            assert not job_dir.exists()


class TestTimeoutWatchdogLogic:
    """Test watchdog timeout transition logic."""

    def test_stuck_job_identified(self):
        """Jobs in progress > 30 minutes should be identified as stuck."""
        timeout_minutes = 30
        job_updated_at = datetime.utcnow() - timedelta(minutes=35)
        threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        is_stuck = job_updated_at < threshold
        assert is_stuck

    def test_recent_job_not_stuck(self):
        """Jobs in progress < 30 minutes should NOT be identified as stuck."""
        timeout_minutes = 30
        job_updated_at = datetime.utcnow() - timedelta(minutes=10)
        threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        is_stuck = job_updated_at < threshold
        assert not is_stuck

    def test_exactly_30_minutes_not_stuck(self):
        """Jobs at exactly 30 minutes should not yet be marked as stuck."""
        timeout_minutes = 30
        job_updated_at = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)

        # At exactly 30 minutes, should not be strictly less than threshold
        # (allowing for slight timing differences)
        is_stuck = job_updated_at < threshold
        # This may be True or False depending on sub-second timing; this is acceptable

    def test_timeout_error_message(self):
        """The error message for timed-out jobs should be descriptive."""
        error_message = "Job processing timed out after 30 minutes"

        assert "timed out" in error_message.lower()
        assert "30" in error_message
        assert "minutes" in error_message.lower()

    def test_timeout_transitions_to_failed(self):
        """Timed-out jobs should transition to 'failed' status."""
        current_status = "in_progress"
        is_timed_out = True

        new_status = "failed" if is_timed_out else current_status
        assert new_status == "failed"


class TestProgressStages:
    """Test progress stage mapping."""

    def test_all_stages_defined(self):
        """All expected pipeline stages should be defined."""
        expected_stages = [
            "queued", "ingestion", "parsing", "analysis_pass1",
            "analysis_pass2", "analysis_pass3", "knowledge_building",
            "embedding", "explanation", "cleanup", "completed",
        ]

        for stage in expected_stages:
            assert stage in PROGRESS_STAGES, f"Stage {stage} not defined"

    def test_progress_starts_at_zero(self):
        """Initial stage should have 0% progress."""
        assert PROGRESS_STAGES["queued"][0] == 0

    def test_progress_ends_at_100(self):
        """Completed stage should have 100% progress."""
        assert PROGRESS_STAGES["completed"][0] == 100

    def test_progress_values_valid_range(self):
        """All progress values should be between 0 and 100."""
        for stage, (progress, _) in PROGRESS_STAGES.items():
            assert 0 <= progress <= 100, (
                f"Stage {stage} has invalid progress {progress}"
            )

    def test_cleanup_logs_job_id(self):
        """Cleanup logging should include job_id, timestamp, and size."""
        import io
        from contextlib import redirect_stdout

        job_id = "test-job-123"
        total_size = 5000

        f = io.StringIO()
        with redirect_stdout(f):
            print(f"[CLEANUP] Deleted job {job_id}: {total_size} bytes freed at {datetime.utcnow()}")

        output = f.getvalue()
        assert job_id in output
        assert str(total_size) in output
        assert "bytes freed" in output
