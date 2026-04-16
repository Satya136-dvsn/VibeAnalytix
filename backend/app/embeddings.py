"""
Embedding provider utilities with provider/model fallback.

This module centralizes embedding generation so all callers share the same
model selection and fallback behavior.
"""

from __future__ import annotations

import asyncio
from typing import Iterable, Optional

import google.generativeai as genai
import httpx
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
_LOCAL_EMBED_CLIENT: httpx.AsyncClient | None = None


def _is_configured_key(value: str | None, *, expected_prefix: str | None = None) -> bool:
    """Return True only for non-placeholder provider keys."""
    if not value:
        return False
    key = value.strip()
    if not key:
        return False
    if "placeholder" in key.lower():
        return False
    if expected_prefix and not key.startswith(expected_prefix):
        return False
    return True


def _get_openai_client() -> AsyncOpenAI:
    """Lazily initialize and cache OpenAI client."""
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        _OPENAI_CLIENT = AsyncOpenAI(api_key=settings.openai_api_key)
    return _OPENAI_CLIENT


def _get_local_embed_client() -> httpx.AsyncClient:
    """Lazily initialize and cache local embedding HTTP client."""
    global _LOCAL_EMBED_CLIENT
    if _LOCAL_EMBED_CLIENT is None:
        _LOCAL_EMBED_CLIENT = httpx.AsyncClient(
            timeout=float(settings.local_embedding_timeout_seconds)
        )
    return _LOCAL_EMBED_CLIENT


async def close_local_embed_client() -> None:
    """Release shared local embedding HTTP resources."""
    global _LOCAL_EMBED_CLIENT
    if _LOCAL_EMBED_CLIENT is not None:
        await _LOCAL_EMBED_CLIENT.aclose()
        _LOCAL_EMBED_CLIENT = None


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


async def _local_embed_content(content: str) -> list[float]:
    """Call local Ollama-compatible embedding endpoint."""
    base_url = settings.local_embedding_base_url.rstrip("/")
    payload = {
        "model": settings.local_embedding_model,
        "input": content,
    }

    client = _get_local_embed_client()
    response = await client.post(f"{base_url}/api/embed", json=payload)
    response.raise_for_status()
    data = response.json()

    embeddings = data.get("embeddings")
    if isinstance(embeddings, list) and embeddings:
        first = embeddings[0]
        if isinstance(first, list) and first:
            return [float(v) for v in first]

    embedding = data.get("embedding")
    if isinstance(embedding, list) and embedding:
        return [float(v) for v in embedding]

    raise RuntimeError("Local embedding provider returned no embedding vector")


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

    embed_mode = settings.embedding_provider_mode
    use_local = embed_mode in {"local", "hybrid"}
    use_cloud = embed_mode in {"cloud", "hybrid"}

    if use_local:
        try:
            return await _local_embed_content(content)
        except Exception as exc:  # pragma: no cover - local service/network specific
            last_error = exc
            if embed_mode == "local":
                raise

    if use_cloud and _is_configured_key(settings.gemini_api_key, expected_prefix="AIza"):
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

    if use_cloud and _is_configured_key(settings.openai_api_key, expected_prefix="sk-"):
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
        "No embedding provider configured. Configure local embedding service or set cloud API keys."
    )
