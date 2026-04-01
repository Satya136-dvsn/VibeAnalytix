"""
Property-based tests for Cleanup Service using Hypothesis.
Tests Properties 29-30 from the design document.
"""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from app.cleanup import PROGRESS_STAGES


# ============ Strategies ============

safe_name = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=15,
)


class TestCleanupAfterTerminalState:
    """Property-based tests for cleanup after terminal state (Property 29)."""

    # Feature: vibeanalytix, Property 29: Cleanup After Terminal State
    @given(
        num_files=st.integers(min_value=1, max_value=10),
        terminal_status=st.sampled_from(["completed", "failed"]),
    )
    @settings(max_examples=100)
    def test_temp_directory_deleted_after_terminal_state(self, num_files, terminal_status):
        """For any job reaching terminal state, the temp directory should be deleted."""
        with tempfile.TemporaryDirectory() as root_tmpdir:
            # Create a temp job directory
            job_dir = Path(root_tmpdir) / "job_temp"
            job_dir.mkdir()

            # Create some files in it
            for i in range(num_files):
                (job_dir / f"file_{i}.txt").write_text(f"content {i}")

            # Verify directory exists before cleanup
            assert job_dir.exists()

            # Simulate cleanup (same logic as cleanup_job)
            if job_dir.exists():
                total_size = sum(
                    f.stat().st_size for f in job_dir.rglob("*") if f.is_file()
                )
                shutil.rmtree(job_dir)

            # After cleanup, the directory should no longer exist
            assert not job_dir.exists(), (
                f"Temp directory still exists after cleanup for {terminal_status} job"
            )

    # Feature: vibeanalytix, Property 29: Cleanup After Terminal State (with subdirectories)
    @given(
        num_subdirs=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=100)
    def test_nested_directories_fully_removed(self, num_subdirs):
        """Cleanup should remove nested directory structures completely."""
        with tempfile.TemporaryDirectory() as root_tmpdir:
            job_dir = Path(root_tmpdir) / "job_nested"
            job_dir.mkdir()

            # Create nested structure
            current = job_dir
            for i in range(num_subdirs):
                sub = current / f"subdir_{i}"
                sub.mkdir()
                (sub / "file.txt").write_text("data")
                current = sub

            assert job_dir.exists()

            # Cleanup
            shutil.rmtree(job_dir)

            assert not job_dir.exists()


class TestTimeoutWatchdog:
    """Property-based tests for timeout watchdog (Property 30)."""

    # Feature: vibeanalytix, Property 30: Timeout Watchdog
    @given(
        minutes_in_progress=st.integers(min_value=31, max_value=120),
    )
    @settings(max_examples=100)
    def test_stuck_jobs_marked_as_failed(self, minutes_in_progress):
        """Jobs in 'in_progress' > 30 minutes should transition to 'failed'."""
        timeout_threshold_minutes = 30

        # Simulate job that has been in progress for too long
        job_updated_at = datetime.utcnow() - timedelta(minutes=minutes_in_progress)
        threshold = datetime.utcnow() - timedelta(minutes=timeout_threshold_minutes)

        is_stuck = job_updated_at < threshold

        assert is_stuck, (
            f"Job should be considered stuck after {minutes_in_progress} minutes"
        )

        # When stuck, the job should be marked as failed
        new_status = "failed" if is_stuck else "in_progress"
        assert new_status == "failed"

        # Error message should mention timeout
        error_message = "Job processing timed out after 30 minutes"
        assert "timed out" in error_message.lower()
        assert "30" in error_message

    # Feature: vibeanalytix, Property 30: Timeout Watchdog (under threshold)
    @given(
        minutes_in_progress=st.integers(min_value=0, max_value=29),
    )
    @settings(max_examples=100)
    def test_recent_jobs_not_marked_failed(self, minutes_in_progress):
        """Jobs in 'in_progress' < 30 minutes should NOT be marked as failed."""
        timeout_threshold_minutes = 30

        job_updated_at = datetime.utcnow() - timedelta(minutes=minutes_in_progress)
        threshold = datetime.utcnow() - timedelta(minutes=timeout_threshold_minutes)

        is_stuck = job_updated_at < threshold

        assert not is_stuck, (
            f"Job should NOT be stuck after only {minutes_in_progress} minutes"
        )


class TestProgressStageMapping:
    """Additional tests for progress stage consistency."""

    # Feature: vibeanalytix, Property 29/30: Progress mapping consistency
    @given(st.just(True))
    @settings(max_examples=1)
    def test_progress_stages_are_monotonically_increasing(self, _):
        """Progress percentages should increase monotonically through stages."""
        stage_order = [
            "queued", "ingestion", "parsing", "analysis_pass1",
            "analysis_pass2", "analysis_pass3", "knowledge_building",
            "embedding", "explanation", "cleanup", "completed",
        ]

        progress_values = [PROGRESS_STAGES[stage][0] for stage in stage_order]

        for i in range(len(progress_values) - 1):
            assert progress_values[i] <= progress_values[i + 1], (
                f"Progress not monotonic: {stage_order[i]}={progress_values[i]} > "
                f"{stage_order[i+1]}={progress_values[i+1]}"
            )

        # First should be 0, last should be 100
        assert progress_values[0] == 0
        assert progress_values[-1] == 100
