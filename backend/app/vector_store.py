"""
Vector storage and retrieval using pgvector.

Handles:
- Cosine similarity search for semantic retrieval
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FunctionSummary


def _format_vector_for_pgvector(embedding: list[float]) -> str:
    """
    Format a Python list as a pgvector array literal string.

    pgvector expects vectors in the format '[0.1, 0.2, 0.3]'
    We use string formatting to create this safely.

    Args:
        embedding: List of floats

    Returns:
        String representation of the vector for pgvector
    """
    # Format as pgvector array literal: '[0.1, 0.2, ...]'
    formatted_values = ", ".join(str(x) for x in embedding)
    return f"[{formatted_values}]"


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
    # Format the query embedding as a pgvector array literal string
    query_vector_str = _format_vector_for_pgvector(query_embedding)

    # Use raw SQL with pgvector's array literal syntax
    # The vector literal '[...]' is passed directly in the ORDER BY clause
    result = await session.execute(
        text("""
            SELECT id, job_id, file_path, function_name, line_start, line_end,
                   summary_text, embedding
            FROM function_summaries
            WHERE job_id = :job_id AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:query_vector AS vector)
            LIMIT :top_k
        """),
        {
            "job_id": str(job_id),
            "query_vector": query_vector_str,
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
