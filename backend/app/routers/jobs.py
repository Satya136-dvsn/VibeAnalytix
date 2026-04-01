"""
Jobs router for job submission, status tracking, and results retrieval.
"""

import asyncio
import tempfile
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

from app.auth import get_current_user
from app.database import get_session
from app.models import User, Job, ProjectResult, FileSummary
from app.schemas import (
    JobSubmissionResponse,
    JobStatusResponse,
    JobResultsResponse,
    ErrorResponse,
    ExplanationSet,
)
from app.tasks import run_pipeline
from app.celery_app import celery_app

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _is_valid_github_url(url: str) -> bool:
    """Validate GitHub URL format."""
    import re
    pattern = r"^https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?$"
    return bool(re.match(pattern, url.strip()))


@router.post(
    "",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
async def submit_job(
    github_url: str = Form(None),
    zip_file: UploadFile = File(None),
    idempotency_key: str = Form(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobSubmissionResponse:
    """
    Submit a job for analysis.

    Either github_url or zip_file must be provided (not both).

    Args:
        github_url: GitHub repository URL
        zip_file: ZIP file upload
        idempotency_key: Optional idempotency key for duplicate detection
        user: Authenticated user
        session: Database session

    Returns:
        Job submission response with job_id

    Raises:
        HTTPException 400: If validation fails
        HTTPException 429: If rate limit exceeded
    """
    # Validate input
    if not github_url and not zip_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either github_url or zip_file must be provided",
        )

    if github_url and zip_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of github_url or zip_file can be provided",
        )

    # Check rate limit (10 jobs per hour)
    from datetime import datetime, timedelta
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    stmt = select(Job).where(
        (Job.user_id == user.id) &
        (Job.created_at >= one_hour_ago)
    )
    result = await session.execute(stmt)
    recent_jobs = result.scalars().all()

    if len(recent_jobs) >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: 10 jobs per hour",
        )

    # Check idempotency
    if idempotency_key:
        # In production, implement proper idempotency key tracking
        pass

    # Process based on source type
    source_type: str
    source_ref: str

    if github_url:
        if not _is_valid_github_url(github_url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid GitHub URL format. Expected: https://github.com/owner/repo",
            )

        source_type = "github"
        source_ref = github_url.strip()

    else:  # zip_file
        if not zip_file.filename.endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must have .zip extension",
            )

        # Read uploaded file bytes
        file_bytes = await zip_file.read()

        import base64
        source_type = "zip"
        source_ref = base64.b64encode(file_bytes).decode('utf-8')

    # Create job record
    job = Job(
        user_id=user.id,
        source_type=source_type,
        source_ref=source_ref,
        status="queued",
        progress_pct=0,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Enqueue pipeline task
    run_pipeline.delay(str(job.id), source_type, source_ref)

    return JobSubmissionResponse(
        job_id=job.id,
        status="queued",
    )


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_job_status(
    job_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobStatusResponse:
    """
    Get job status and progress.

    Args:
        job_id: Job identifier
        user: Authenticated user
        session: Database session

    Returns:
        Job status response

    Raises:
        HTTPException 404: If job not found
        HTTPException 403: If user doesn't own the job
    """
    # Find job
    stmt = select(Job).where(Job.id == UUID(job_id))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check authorization
    if job.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        current_stage=job.current_stage,
        progress_pct=job.progress_pct,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get(
    "/{job_id}/results",
    response_model=JobResultsResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def get_job_results(
    job_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobResultsResponse:
    """
    Get completed job results and explanations.

    Args:
        job_id: Job identifier
        user: Authenticated user
        session: Database session

    Returns:
        Complete job results

    Raises:
        HTTPException 404: If job not found
        HTTPException 403: If user doesn't own the job
    """
    # Find job
    stmt = select(Job).where(Job.id == UUID(job_id))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check authorization
    if job.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get project results
    stmt = select(ProjectResult).where(ProjectResult.job_id == UUID(job_id))
    result = await session.execute(stmt)
    project_result = result.scalar_one_or_none()

    if not project_result:
        # Results not yet available
        explanations = ExplanationSet()
    else:
        per_file_explanations = project_result.per_file_explanations or {}

        explanations = ExplanationSet(
            project_summary=project_result.project_summary,
            overview_explanation=project_result.overview_explanation,
            flow_explanation=project_result.flow_explanation,
            per_file_explanations=per_file_explanations,
            dependency_graph=project_result.dependency_graph,
            entry_points=project_result.entry_points,
            circular_deps=project_result.circular_deps,
            external_deps=project_result.external_deps,
            file_tree=project_result.file_tree,
        )

    return JobResultsResponse(
        job_id=job.id,
        status=job.status,
        explanations=explanations,
    )


@router.post(
    "/{job_id}/retry",
    response_model=JobSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
async def retry_job(
    job_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobSubmissionResponse:
    """
    Retry a failed job.

    Args:
        job_id: Job identifier
        user: Authenticated user
        session: Database session

    Returns:
        New job submission response

    Raises:
        HTTPException 404: If job not found
        HTTPException 403: If user doesn't own the job
        HTTPException 400: If job is not in failed state
    """
    # Find job
    stmt = select(Job).where(Job.id == UUID(job_id))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # Check authorization
    if job.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Check job state
    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed jobs can be retried",
        )

    # Create new job with same parameters
    new_job = Job(
        user_id=user.id,
        source_type=job.source_type,
        source_ref=job.source_ref,
        status="queued",
        progress_pct=0,
    )
    session.add(new_job)
    await session.commit()
    await session.refresh(new_job)

    # Enqueue pipeline
    run_pipeline.delay(str(new_job.id), job.source_type, job.source_ref)

    return JobSubmissionResponse(
        job_id=new_job.id,
        status="queued",
    )
