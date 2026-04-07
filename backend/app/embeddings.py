"""
Embedding provider utilities with provider/model fallback.

This module centralizes embedding generation so all callers share the same
model selection and fallback behavior.
"""

from __future__ import annotations

import asyncio
from typing import Iterable, Optional

import google.generativeai as genai
from openai import AsyncOpenAI

from app.config import settings


GEMINI_EMBED_MODELS: tuple[str, ...] = (
    "models/gemini-embedding-001",
    "gemini-embedding-001",
    "models/text-embedding-004",
    "text-embedding-004",
)

_GENAI_CONFIGURED = False
_OPENAI_CLIENT: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    """Lazily initialize and cache OpenAI client."""
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        _OPENAI_CLIENT = AsyncOpenAI(api_key=settings.openai_api_key)
    return _OPENAI_CLIENT


def _ensure_genai_configured() -> None:
    """Configure Gemini SDK once per process."""
    global _GENAI_CONFIGURED
    if not _GENAI_CONFIGURED:
        genai.configure(api_key=settings.gemini_api_key)
        _GENAI_CONFIGURED = True


async def _gemini_embed_content(model: str, content: str, task_type: str) -> object:
    """Call Gemini embeddings API with compatibility across SDK versions."""
    if hasattr(genai, "embed_content_async"):
        return await genai.embed_content_async(
            model=model,
            content=content,
            task_type=task_type,
        )

    return await asyncio.to_thread(
        genai.embed_content,
        model=model,
        content=content,
        task_type=task_type,
    )


def _coerce_embedding(raw: object) -> Optional[list[float]]:
    """Normalize provider-specific embedding payloads into list[float]."""
    if raw is None:
        return None

    if isinstance(raw, dict):
        embedding = raw.get("embedding")
    else:
        embedding = getattr(raw, "embedding", None)

    if embedding is None:
        return None

    # google.generativeai may return an object exposing .values
    values = getattr(embedding, "values", embedding)
    if isinstance(values, Iterable) and not isinstance(values, (str, bytes, dict)):
        return [float(x) for x in values]

    return None


async def generate_embedding(
    text: str,
    *,
    task_type: str = "retrieval_query",
) -> list[float]:
    """
    Generate an embedding vector using Gemini with model fallback, then OpenAI.

    Raises the final provider error if no configured provider succeeds.
    """
    content = text[:8000]
    last_error: Exception | None = None

    if settings.gemini_api_key:
        _ensure_genai_configured()
        for model in GEMINI_EMBED_MODELS:
            try:
                response = await _gemini_embed_content(
                    model=model,
                    content=content,
                    task_type=task_type,
                )
                embedding = _coerce_embedding(response)
                if embedding:
                    return embedding
            except Exception as exc:  # pragma: no cover - provider/network specific
                last_error = exc

    if settings.openai_api_key:
        try:
            client = _get_openai_client()
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=content,
            )
            return response.data[0].embedding
        except Exception as exc:  # pragma: no cover - provider/network specific
            last_error = exc

    if last_error:
        raise last_error

    raise RuntimeError(
        "No embedding provider configured. Set GEMINI_API_KEY or OPENAI_API_KEY."
    )
