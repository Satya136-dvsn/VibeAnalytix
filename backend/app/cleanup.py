"""
Cleanup Service for deleting temporary files and managing job lifecycle.
"""

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Job


async def cleanup_job(
    job_id: str,
    temp_dir: Path,
    session: AsyncSession,
) -> tuple[bool, int]:
    """
    Delete temporary files associated with a job.

    Args:
        job_id: Job identifier
        temp_dir: Temporary directory to delete
        session: Database session

    Returns:
        Tuple of (success, bytes_freed)
    """
    try:
        if temp_dir.exists():
            # Calculate size before deletion
            total_size = 0
            for f in temp_dir.rglob("*"):
                if f.is_file():
                    total_size += f.stat().st_size

            # Delete directory
            shutil.rmtree(temp_dir)

            # Log deletion
            print(f"[CLEANUP] Deleted job {job_id}: {total_size} bytes freed at {datetime.utcnow()}")

            return True, total_size

        return True, 0

    except Exception as e:
        print(f"[CLEANUP] Error deleting {temp_dir}: {e}")
        return False, 0


async def cleanup_on_completion(
    job_id: str,
    temp_dir: Path,
    session: AsyncSession,
) -> None:
    """
    Clean up after job completion or failure.

    Args:
        job_id: Job identifier
        temp_dir: Temporary directory
        session: Database session
    """
    success, bytes_freed = await cleanup_job(job_id, temp_dir, session)

    if not success:
        print(f"[CLEANUP] Failed to cleanup job {job_id}")


async def timeout_watchdog(session: AsyncSession) -> None:
    """
    Watchdog task to mark jobs stuck in 'in_progress' for > 30 minutes as failed.

    Runs periodically via Celery beat.

    Args:
        session: Database session
    """
    timeout_threshold = datetime.utcnow() - timedelta(
        minutes=settings.cleanup_timeout_minutes
    )

    try:
        # Find jobs stuck in progress
        stmt = select(Job).where(
            (Job.status == "in_progress") &
            (Job.updated_at < timeout_threshold)
        )
        result = await session.execute(stmt)
        stuck_jobs = result.scalars().all()

        for job in stuck_jobs:
            print(
                f"[WATCHDOG] Job {job.id} timed out. "
                f"Updated at {job.updated_at}, threshold {timeout_threshold}"
            )

            # Mark as failed
            stmt = (
                update(Job)
                .where(Job.id == job.id)
                .values(
                    status="failed",
                    error_message="Job processing timed out after 30 minutes",
                    updated_at=datetime.utcnow(),
                )
            )
            await session.execute(stmt)

            # Attempt cleanup
            temp_dir = Path("/tmp") / "vibeanalytix" / str(job.id)
            await cleanup_on_completion(str(job.id), temp_dir, session)

        await session.commit()

        print(f"[WATCHDOG] Processed {len(stuck_jobs)} timed-out jobs")

    except Exception as e:
        print(f"[WATCHDOG] Error in watchdog: {e}")
        await session.rollback()


# Progress stage mapping
PROGRESS_STAGES = {
    "queued": (0, "queued"),
    "ingestion": (15, "ingestion"),
    "parsing": (30, "parsing"),
    "analysis_pass1": (40, "analysis_pass1"),
    "analysis_pass2": (50, "analysis_pass2"),
    "analysis_pass3": (60, "analysis_pass3"),
    "knowledge_building": (70, "knowledge_building"),
    "embedding": (80, "embedding"),
    "explanation": (90, "explanation"),
    "cleanup": (100, "cleanup"),
    "completed": (100, "completed"),
}


async def update_job_progress(
    job_id: str,
    stage: str,
    progress_pct: int,
    session: AsyncSession,
) -> None:
    """
    Update job progress in database.

    Args:
        job_id: Job identifier
        stage: Current pipeline stage
        progress_pct: Progress percentage (0-100)
        session: Database session
    """
    try:
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(
                current_stage=stage,
                progress_pct=progress_pct,
                status="in_progress" if progress_pct < 100 else "completed",
                updated_at=datetime.utcnow(),
            )
        )
        await session.execute(stmt)
        await session.commit()
    except Exception as e:
        print(f"[PROGRESS] Error updating job {job_id}: {e}")


async def mark_job_failed(
    job_id: str,
    error_message: str,
    session: AsyncSession,
) -> None:
    """
    Mark a job as failed with error message.

    Args:
        job_id: Job identifier
        error_message: Error description
        session: Database session
    """
    try:
        stmt = (
            update(Job)
            .where(Job.id == job_id)
            .values(
                status="failed",
                error_message=error_message,
                updated_at=datetime.utcnow(),
            )
        )
        await session.execute(stmt)
        await session.commit()
    except Exception as e:
        print(f"[ERROR] Failed to mark job {job_id} as failed: {e}")
