"""
Repository Q&A service built on semantic retrieval and the explanation engine.
"""

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings import generate_embedding
from app.explanation_engine import ExplanationEngine
from app.vector_store import hybrid_retrieval

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
) -> tuple[str, list[dict], float, bool, str | None]:
    """Answer a repository question using semantic retrieval and LLM synthesis."""
    query_embedding = await generate_embedding(
        query,
        task_type="retrieval_query",
    )

    top_candidates = await hybrid_retrieval(
        session=session,
        job_id=UUID(job_id),
        query_text=query,
        query_embedding=query_embedding,
        top_k=8,
    )

    if not top_candidates:
        return (
            "I do not have enough repository evidence to answer this yet. "
            "Run analysis completion checks and try a more specific question with file/function names.",
            [],
            0.0,
            True,
            "no_retrieval_results",
        )

    top_score = float(top_candidates[0].get("score", 0.0))
    avg_top = sum(float(c.get("score", 0.0)) for c in top_candidates[:3]) / min(3, len(top_candidates))
    confidence = max(0.0, min(1.0, 0.7 * top_score + 0.3 * avg_top))

    # Guardrail: abstain when retrieval confidence is too weak.
    if confidence < 0.3:
        weak_sources = []
        for item in top_candidates[:3]:
            fn = item["summary"]
            weak_sources.append(
                {
                    "file": fn.file_path,
                    "function": fn.function_name,
                    "summary": fn.summary_text,
                    "score": round(float(item.get("score", 0.0)), 4),
                }
            )
        return (
            "I cannot answer with high confidence from the available evidence. "
            "Please refine the question with specific files, functions, or expected behavior.",
            weak_sources,
            confidence,
            True,
            "low_retrieval_confidence",
        )

    sources = []
    context_parts = []
    for item in top_candidates:
        fn = item["summary"]
        sources.append(
            {
                "file": fn.file_path,
                "function": fn.function_name,
                "summary": fn.summary_text,
                "score": round(float(item.get("score", 0.0)), 4),
                "semantic_score": round(float(item.get("semantic_score", 0.0)), 4),
                "lexical_score": round(float(item.get("lexical_score", 0.0)), 4),
            }
        )
        context_parts.append(
            f"File: {fn.file_path}\n"
            f"Function: {fn.function_name} (Lines {fn.line_start}-{fn.line_end})\n"
            f"Summary: {fn.summary_text}\n"
            f"Relevance score: {round(float(item.get('score', 0.0)), 4)}"
        )

    context_str = "\n\n".join(context_parts)
    system_prompt = (
        "You are a helpful senior developer analyzing a codebase. "
        "Answer ONLY from the provided repository context and never invent implementation details. "
        "When uncertain, explicitly state uncertainty. "
        "Cite relevant evidence inline using [file:function] from the snippets."
    )
    user_prompt = (
        f"Context from codebase:\n{context_str}\n\n"
        f"Question: {query}\n\n"
        "Output format requirements:\n"
        "- Start with a direct answer in 2-5 sentences.\n"
        "- Then add a short 'Evidence' bullet list with citations like [path:function].\n"
        "- If context does not support a claim, say so clearly."
    )

    if engine is None:
        engine = await get_shared_explanation_engine()

    async def _create():
        return await engine._call_provider_llm(system_prompt, user_prompt)

    answer = await engine._retry_with_backoff(_create)
    if not isinstance(answer, str) or not answer.strip():
        answer = (
            "I could not produce a reliable response from the current context. "
            "Try asking a narrower question tied to specific code paths."
        )

    return answer, sources, confidence, False, None
