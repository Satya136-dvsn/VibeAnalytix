"""
Jobs router for job submission, status tracking, and results retrieval.
"""

import asyncio
import json
import tempfile
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form

from app.auth import get_current_user
from app.config import settings
from app.database import get_session
from app.models import User, Job, ProjectResult, FileSummary
from app.rate_limiter import enforce_sliding_window_limit, RateLimitError
from app.redis_store import get_redis
from app.schemas import (
    JobSubmissionResponse,
    JobStatusResponse,
    JobResultsResponse,
    ErrorResponse,
    ExplanationSet,
    ChatRequest,
    ChatResponse,
)
from app.tasks import run_pipeline
from app.celery_app import celery_app

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


async def check_idempotency_key(
    idempotency_key: str,
    user_id: UUID,
    session: AsyncSession,
) -> UUID | None:
    """
    Check if idempotency key exists and return existing job_id if found.
    
    Args:
        idempotency_key: The idempotency key to check
        user_id: User ID to namespace the key
        session: Database session
        
    Returns:
        Existing job_id if found and within 24 hours, None otherwise
    """
    if not idempotency_key:
        return None
    
    redis_client = await get_redis()
    
    # Redis key: "idempotency:{user_id}:{key}"
    cache_key = f"idempotency:{user_id}:{idempotency_key}"
    
    stored_value = await redis_client.get(cache_key)
    if stored_value:
        job_id_str = json.loads(stored_value)["job_id"]
        # Verify job still exists
        job = await session.get(Job, UUID(job_id_str))
        if job:
            return UUID(job_id_str)
    
    return None


async def store_idempotency_key(
    idempotency_key: str,
    user_id: UUID,
    job_id: UUID,
) -> None:
    """
    Store idempotency key with job_id for 24 hours.
    
    Args:
        idempotency_key: The idempotency key to store
        user_id: User ID to namespace the key
        job_id: Job ID to store
    """
    if not idempotency_key:
        return
    
    redis_client = await get_redis()
    
    # Redis key: "idempotency:{user_id}:{key}"
    cache_key = f"idempotency:{user_id}:{idempotency_key}"
    
    # Store with 24-hour TTL
    value = json.dumps({"job_id": str(job_id)})
    await redis_client.setex(cache_key, 86400, value)  # 86400 seconds = 24 hours


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

    # Redis sliding-window rate limit (production-safe)
    try:
        await enforce_sliding_window_limit(
            key=f"rate_limit:jobs:user:{user.id}",
            limit=settings.rate_limit_jobs_per_hour,
            window_seconds=3600,
        )
    except RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: "
                f"{settings.rate_limit_jobs_per_hour} job submissions per hour"
            ),
        )

    # Check idempotency — if key exists, return existing job
    if idempotency_key:
        existing_job_id = await check_idempotency_key(idempotency_key, user.id, session)
        if existing_job_id:
            return JobSubmissionResponse(
                job_id=existing_job_id,
                status="queued",  # May have progressed, but we return queued for consistency
            )

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

    # Store idempotency key for future duplicate detection
    if idempotency_key:
        await store_idempotency_key(idempotency_key, user.id, job.id)

    # Enqueue pipeline task
    run_pipeline.delay(str(job.id), source_type, source_ref)

    return JobSubmissionResponse(
        job_id=job.id,
        status="queued",
    )


@router.get(
    "",
    response_model=list[JobStatusResponse],
    responses={
        401: {"model": ErrorResponse},
    },
)
async def get_user_jobs(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[JobStatusResponse]:
    """
    Get all jobs for current user, ordered by creation date descending.
    """
    stmt = select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc())
    result = await session.execute(stmt)
    jobs = result.scalars().all()
    
    return [
        JobStatusResponse(
            job_id=job.id,
            source_type=job.source_type,
            source_ref=job.source_ref,
            status=job.status,
            current_stage=job.current_stage,
            progress_pct=job.progress_pct,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        for job in jobs
    ]


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
        source_type=job.source_type,
        source_ref=job.source_ref,
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
        source_type=job.source_type,
        source_ref=job.source_ref,
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


@router.post(
    "/{job_id}/chat",
    response_model=ChatResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def chat_with_repo(
    job_id: str,
    request: ChatRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    """
    Ask a question about the analyzed codebase using semantic vector search.
    """
    from app.vector_store import semantic_retrieval
    from app.config import settings
    import google.generativeai as genai
    from openai import AsyncOpenAI

    # Find job
    stmt = select(Job).where(Job.id == UUID(job_id))
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job must be completed to chat")

    try:
        await enforce_sliding_window_limit(
            key=f"rate_limit:chat:user:{user.id}",
            limit=settings.rate_limit_chat_per_minute,
            window_seconds=60,
        )
    except RateLimitError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: "
                f"{settings.rate_limit_chat_per_minute} chat requests per minute"
            ),
        )

    try:
        # Generate query embedding
        gemini_mode = bool(settings.gemini_api_key)
        if gemini_mode:
            genai.configure(api_key=settings.gemini_api_key)
            response = await genai.embed_content_async(
                model="text-embedding-004",
                content=request.query[:8000],
                task_type="retrieval_query",
            )
            query_embedding = response['embedding'].values
        else:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=request.query[:8000],
            )
            query_embedding = response.data[0].embedding

        # Retrieve top 5 similar functions
        top_functions = await semantic_retrieval(
            session=session,
            job_id=job.id,
            query_embedding=query_embedding,
            top_k=5,
        )

        sources = []
        context_parts = []
        for fn in top_functions:
            sources.append({
                "file": fn.file_path,
                "function": fn.function_name,
                "summary": fn.summary_text
            })
            context_parts.append(
                f"File: {fn.file_path}\n"
                f"Function: {fn.function_name} (Lines {fn.line_start}-{fn.line_end})\n"
                f"Summary: {fn.summary_text}"
            )

        context_str = "\n\n".join(context_parts)
        
        system_prompt = (
            "You are a helpful senior developer analyzing a codebase. "
            "Use the provided context snippets from the codebase to answer the user's question. "
            "If the context is insufficient, explain what you can infer, but don't invent code."
        )
        user_prompt = f"Context from codebase:\n{context_str}\n\nQuestion: {request.query}"

        # Get answer
        if gemini_mode:
            model = genai.GenerativeModel("gemini-1.5-flash")
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            chat_response = await model.generate_content_async(
                full_prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.3)
            )
            answer = chat_response.text
        else:
            chat_response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            answer = chat_response.choices[0].message.content

        return ChatResponse(answer=answer, sources=sources)

    except Exception as e:
        import logging
        logging.error(f"Chat error: {e}")
        # Return graceful degradation if AI fails
        return ChatResponse(
            answer=f"I couldn't process your request dynamically due to: {str(e)} However, based on the repository structure, try manually inspecting the files mentioned in your analysis overview.",
            sources=[]
        )

