"""
Repository Q&A service built on semantic retrieval and the explanation engine.
"""

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings import generate_embedding
from app.explanation_engine import ExplanationEngine
from app.vector_store import semantic_retrieval

_SHARED_ENGINE: ExplanationEngine | None = None
_SHARED_ENGINE_LOCK = asyncio.Lock()


async def get_shared_explanation_engine() -> ExplanationEngine:
    """Reuse a single explanation engine instance for request handlers."""
    global _SHARED_ENGINE
    if _SHARED_ENGINE is None:
        async with _SHARED_ENGINE_LOCK:
            if _SHARED_ENGINE is None:
                _SHARED_ENGINE = ExplanationEngine()
    return _SHARED_ENGINE


async def answer_repository_question(
    job_id: str,
    query: str,
    session: AsyncSession,
    engine: ExplanationEngine | None = None,
) -> tuple[str, list[dict]]:
    """Answer a repository question using semantic retrieval and LLM synthesis."""
    query_embedding = await generate_embedding(
        query,
        task_type="retrieval_query",
    )

    top_functions = await semantic_retrieval(
        session=session,
        job_id=UUID(job_id),
        query_embedding=query_embedding,
        top_k=5,
    )

    sources = []
    context_parts = []
    for fn in top_functions:
        sources.append(
            {
                "file": fn.file_path,
                "function": fn.function_name,
                "summary": fn.summary_text,
            }
        )
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
    user_prompt = f"Context from codebase:\n{context_str}\n\nQuestion: {query}"

    if engine is None:
        engine = await get_shared_explanation_engine()

    async def _create():
        return await engine._call_provider_llm(system_prompt, user_prompt)

    answer = await engine._retry_with_backoff(_create)
    return answer, sources
