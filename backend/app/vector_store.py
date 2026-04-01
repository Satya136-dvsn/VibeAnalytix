"""
Vector storage and retrieval using pgvector.

Handles:
- Cosine similarity search for semantic retrieval
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, text, cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FunctionSummary


async def semantic_retrieval(
    session: AsyncSession,
    job_id: UUID,
    query_embedding: list[float],
    top_k: int = 10,
) -> list[FunctionSummary]:
    """
    Retrieve top-k semantically similar function summaries using cosine similarity.

    Uses pgvector's <=> (cosine distance) operator for similarity search.

    Args:
        session: Database session
        job_id: UUID of the job to search within
        query_embedding: Query embedding vector as a list of floats
        top_k: Number of results to return

    Returns:
        List of FunctionSummary records ordered by similarity (most similar first)
    """
    # Use pgvector's array literal syntax for the query
    # Cast the query embedding array to vector type
    query_vector = cast(query_embedding, "vector")

    result = await session.execute(
        text("""
            SELECT id, job_id, file_path, function_name, line_start, line_end,
                   summary_text, embedding
            FROM function_summaries
            WHERE job_id = :job_id AND embedding IS NOT NULL
            ORDER BY embedding <=> cast(:query_embedding as vector)
            LIMIT :top_k
        """),
        {
            "job_id": str(job_id),
            "query_embedding": str(query_embedding),
            "top_k": top_k,
        },
    )
    rows = result.fetchall()

    summaries = []
    for row in rows:
        summary = FunctionSummary(
            id=row[0],
            job_id=row[1],
            file_path=row[2],
            function_name=row[3],
            line_start=row[4],
            line_end=row[5],
            summary_text=row[6],
            embedding=row[7],  # Already a list from pgvector
        )
        summaries.append(summary)

    return summaries


async def get_embeddings_by_job(
    session: AsyncSession,
    job_id: UUID,
) -> list[FunctionSummary]:
    """
    Get all function summaries with embeddings for a job.

    Args:
        session: Database session
        job_id: UUID of the job

    Returns:
        List of FunctionSummary records with embeddings
    """
    result = await session.execute(
        select(FunctionSummary).where(
            FunctionSummary.job_id == job_id,
            FunctionSummary.embedding.isnot(None),
        )
    )
    return list(result.scalars().all())
