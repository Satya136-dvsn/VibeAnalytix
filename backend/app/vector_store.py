"""
Vector storage and retrieval using pgvector.

Handles:
- Cosine similarity search for semantic retrieval
- Hybrid retrieval with lexical + semantic reranking
"""

import re
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


def _tokenize(text: str) -> list[str]:
    """Tokenize to lowercase alphanumeric tokens."""
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


def _lexical_score(query_tokens: list[str], summary: FunctionSummary) -> float:
    """Compute lexical relevance score using token overlap and field boosts."""
    if not query_tokens:
        return 0.0

    name_tokens = _tokenize(summary.function_name or "")
    path_tokens = _tokenize(summary.file_path or "")
    text_tokens = _tokenize(summary.summary_text or "")

    qset = set(query_tokens)
    name_overlap = len(qset.intersection(name_tokens))
    path_overlap = len(qset.intersection(path_tokens))
    text_overlap = len(qset.intersection(text_tokens))

    overlap_ratio = (name_overlap + path_overlap + text_overlap) / max(1, len(qset))

    # Boost exact query term containment in key fields.
    phrase_bonus = 0.0
    qphrase = " ".join(query_tokens)
    combined = f"{summary.function_name} {summary.file_path} {summary.summary_text or ''}".lower()
    if qphrase and qphrase in combined:
        phrase_bonus += 0.15

    name_boost = min(0.3, 0.12 * name_overlap)
    path_boost = min(0.2, 0.08 * path_overlap)
    text_boost = min(0.4, 0.04 * text_overlap)

    return max(0.0, min(1.0, 0.45 * overlap_ratio + name_boost + path_boost + text_boost + phrase_bonus))


def _rerank_bonus(query_tokens: list[str], summary: FunctionSummary) -> float:
    """Apply a small reranking bonus for stronger identifier/path alignment."""
    if not query_tokens:
        return 0.0

    lowered_path = (summary.file_path or "").lower()
    lowered_name = (summary.function_name or "").lower()
    bonus = 0.0

    for token in query_tokens:
        if token in lowered_name:
            bonus += 0.03
        if token in lowered_path:
            bonus += 0.02

    return min(0.2, bonus)


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
    # Backwards-compatible wrapper without exposing scores.
    scored = await semantic_retrieval_scored(
        session=session,
        job_id=job_id,
        query_embedding=query_embedding,
        top_k=top_k,
    )
    return [item["summary"] for item in scored]


async def semantic_retrieval_scored(
    session: AsyncSession,
    job_id: UUID,
    query_embedding: list[float],
    top_k: int = 10,
) -> list[dict]:
    """Retrieve top-k semantically similar summaries with normalized scores."""
    # Format the query embedding as a pgvector array literal string
    query_vector_str = _format_vector_for_pgvector(query_embedding)

    # Use raw SQL with pgvector's array literal syntax
    # The vector literal '[...]' is passed directly in the ORDER BY clause
    result = await session.execute(
        text("""
            SELECT id, job_id, file_path, function_name, line_start, line_end,
                   summary_text, embedding,
                   embedding <=> CAST(:query_vector AS vector) AS distance
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
        distance = float(row[8] or 1.0)
        semantic_score = max(0.0, min(1.0, 1.0 - distance))
        summaries.append(
            {
                "summary": summary,
                "semantic_score": semantic_score,
                "distance": distance,
            }
        )

    return summaries


async def lexical_retrieval_scored(
    session: AsyncSession,
    job_id: UUID,
    query_text: str,
    top_k: int = 10,
    candidate_pool: int = 120,
) -> list[dict]:
    """Retrieve lexical candidates and score using token overlap heuristics."""
    query_tokens = _tokenize(query_text)
    if not query_tokens:
        return []

    pattern = "%" + "%".join(query_tokens[:4]) + "%"

    result = await session.execute(
        text("""
            SELECT id, job_id, file_path, function_name, line_start, line_end,
                   summary_text, embedding
            FROM function_summaries
            WHERE job_id = :job_id
              AND (
                LOWER(COALESCE(summary_text, '')) LIKE LOWER(:pattern)
                OR LOWER(function_name) LIKE LOWER(:pattern)
                OR LOWER(file_path) LIKE LOWER(:pattern)
              )
            LIMIT :candidate_pool
        """),
        {
            "job_id": str(job_id),
            "pattern": pattern,
            "candidate_pool": candidate_pool,
        },
    )
    rows = result.fetchall()

    scored: list[dict] = []
    for row in rows:
        summary = FunctionSummary(
            id=row[0],
            job_id=row[1],
            file_path=row[2],
            function_name=row[3],
            line_start=row[4],
            line_end=row[5],
            summary_text=row[6],
            embedding=row[7],
        )
        lex_score = _lexical_score(query_tokens, summary)
        if lex_score > 0:
            scored.append(
                {
                    "summary": summary,
                    "lexical_score": lex_score,
                }
            )

    scored.sort(key=lambda x: x["lexical_score"], reverse=True)
    return scored[:top_k]


async def hybrid_retrieval(
    session: AsyncSession,
    job_id: UUID,
    query_text: str,
    query_embedding: list[float],
    top_k: int = 10,
) -> list[dict]:
    """Blend semantic and lexical retrieval and rerank the merged candidates."""
    semantic = await semantic_retrieval_scored(
        session=session,
        job_id=job_id,
        query_embedding=query_embedding,
        top_k=max(top_k, top_k * 2),
    )
    lexical = await lexical_retrieval_scored(
        session=session,
        job_id=job_id,
        query_text=query_text,
        top_k=max(top_k, top_k * 2),
    )

    query_tokens = _tokenize(query_text)
    merged: dict[str, dict] = {}

    for item in semantic:
        summary = item["summary"]
        key = str(summary.id)
        merged[key] = {
            "summary": summary,
            "semantic_score": float(item.get("semantic_score", 0.0)),
            "lexical_score": 0.0,
        }

    for item in lexical:
        summary = item["summary"]
        key = str(summary.id)
        if key not in merged:
            merged[key] = {
                "summary": summary,
                "semantic_score": 0.0,
                "lexical_score": float(item.get("lexical_score", 0.0)),
            }
        else:
            merged[key]["lexical_score"] = max(
                merged[key]["lexical_score"],
                float(item.get("lexical_score", 0.0)),
            )

    results: list[dict] = []
    for item in merged.values():
        summary = item["summary"]
        semantic_score = item["semantic_score"]
        lexical_score = item["lexical_score"]
        rerank_bonus = _rerank_bonus(query_tokens, summary)
        combined_score = max(0.0, min(1.0, 0.65 * semantic_score + 0.35 * lexical_score + rerank_bonus))

        results.append(
            {
                "summary": summary,
                "semantic_score": semantic_score,
                "lexical_score": lexical_score,
                "rerank_bonus": rerank_bonus,
                "score": combined_score,
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


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
