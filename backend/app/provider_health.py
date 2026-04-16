"""
Provider readiness checks for local/cloud LLM and embedding backends.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.config import settings


_PROVIDER_HEALTH_CLIENT: httpx.AsyncClient | None = None


def _get_provider_health_client(timeout: float) -> httpx.AsyncClient:
    """Lazily initialize and cache health-check HTTP client."""
    global _PROVIDER_HEALTH_CLIENT
    if _PROVIDER_HEALTH_CLIENT is None:
        _PROVIDER_HEALTH_CLIENT = httpx.AsyncClient(timeout=timeout)
    return _PROVIDER_HEALTH_CLIENT


async def close_provider_health_client() -> None:
    """Release shared health-check HTTP resources."""
    global _PROVIDER_HEALTH_CLIENT
    if _PROVIDER_HEALTH_CLIENT is not None:
        await _PROVIDER_HEALTH_CLIENT.aclose()
        _PROVIDER_HEALTH_CLIENT = None


def _has_valid_key(value: str | None, expected_prefix: str | None = None) -> bool:
    """Return True only for non-placeholder provider keys."""
    if not value:
        return False
    key = value.strip()
    if not key or "placeholder" in key.lower():
        return False
    if expected_prefix and not key.startswith(expected_prefix):
        return False
    return True


async def _fetch_local_models(base_url: str, timeout: float) -> tuple[list[str], str | None]:
    """Query Ollama-compatible tags endpoint and return available model names."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        client = _get_provider_health_client(timeout)
        response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return [], str(exc)

    models = payload.get("models", [])
    if not isinstance(models, list):
        return [], "Unexpected /api/tags payload"

    names: list[str] = []
    for model in models:
        if isinstance(model, dict):
            name = model.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())

    return names, None


def _build_local_component_status(
    *,
    enabled: bool,
    model: str,
    models: list[str],
    error: str | None,
) -> bool:
    """Evaluate local component readiness for one model requirement."""
    if not enabled:
        return True
    return error is None and model in models


def _build_cloud_status() -> dict[str, bool]:
    """Evaluate cloud credential availability."""
    openai_configured = bool((settings.openai_api_key or "").strip())
    gemini_configured = bool((settings.gemini_api_key or "").strip())

    openai_ready = _has_valid_key(settings.openai_api_key, "sk-")
    gemini_ready = _has_valid_key(settings.gemini_api_key, "AIza")

    configured_ready = []
    if openai_configured:
        configured_ready.append(openai_ready)
    if gemini_configured:
        configured_ready.append(gemini_ready)

    all_configured_ready = bool(configured_ready) and all(configured_ready)

    return {
        "openai_configured": openai_configured,
        "openai_ready": openai_ready,
        "gemini_configured": gemini_configured,
        "gemini_ready": gemini_ready,
        "any_ready": openai_ready or gemini_ready,
        "all_configured_ready": all_configured_ready,
    }


def _component_ready(
    mode: str,
    local_ready: bool,
    cloud_any_ready: bool,
    cloud_all_configured_ready: bool,
) -> bool:
    """Resolve readiness by mode with strict hybrid semantics."""
    if mode == "hybrid":
        return local_ready and cloud_all_configured_ready
    if mode == "cloud":
        return cloud_any_ready
    return local_ready


async def get_provider_readiness_report() -> dict[str, Any]:
    """Build a readiness report for local/cloud generation and embeddings."""
    llm_mode = settings.llm_provider_mode
    embedding_mode = settings.embedding_provider_mode

    llm_local_enabled = llm_mode in {"local", "hybrid"}
    embedding_local_enabled = embedding_mode in {"local", "hybrid"}

    llm_models: list[str] = []
    llm_error: str | None = None
    embedding_models: list[str] = []
    embedding_error: str | None = None

    llm_task = _fetch_local_models(
        settings.local_llm_base_url,
        float(settings.local_llm_timeout_seconds),
    ) if llm_local_enabled else None
    embedding_task = _fetch_local_models(
        settings.local_embedding_base_url,
        float(settings.local_embedding_timeout_seconds),
    ) if embedding_local_enabled else None

    if llm_task is not None and embedding_task is not None:
        (llm_models, llm_error), (embedding_models, embedding_error) = await asyncio.gather(
            llm_task,
            embedding_task,
        )
    elif llm_task is not None:
        llm_models, llm_error = await llm_task
    elif embedding_task is not None:
        embedding_models, embedding_error = await embedding_task

    llm_local_ready = _build_local_component_status(
        enabled=llm_local_enabled,
        model=settings.local_llm_model,
        models=llm_models,
        error=llm_error,
    )
    embedding_local_ready = _build_local_component_status(
        enabled=embedding_local_enabled,
        model=settings.local_embedding_model,
        models=embedding_models,
        error=embedding_error,
    )

    cloud_status = _build_cloud_status()
    cloud_any_ready = cloud_status["any_ready"]
    cloud_all_configured_ready = cloud_status["all_configured_ready"]

    llm_ready = _component_ready(
        llm_mode,
        llm_local_ready,
        cloud_any_ready,
        cloud_all_configured_ready,
    )
    embedding_ready = _component_ready(
        embedding_mode,
        embedding_local_ready,
        cloud_any_ready,
        cloud_all_configured_ready,
    )

    overall_ready = llm_ready and embedding_ready

    return {
        "ready": overall_ready,
        "provider_modes": {
            "llm": llm_mode,
            "embedding": embedding_mode,
        },
        "local": {
            "llm_base_url": settings.local_llm_base_url,
            "llm_reachable": llm_error is None if llm_local_enabled else True,
            "llm_error": llm_error,
            "llm_available_models": llm_models,
            "llm_model": settings.local_llm_model,
            "llm_model_ready": llm_local_ready,
            "embedding_base_url": settings.local_embedding_base_url,
            "embedding_reachable": embedding_error is None if embedding_local_enabled else True,
            "embedding_error": embedding_error,
            "embedding_available_models": embedding_models,
            "embedding_model": settings.local_embedding_model,
            "embedding_model_ready": embedding_local_ready,
        },
        "cloud": cloud_status,
        "components": {
            "llm_ready": llm_ready,
            "embedding_ready": embedding_ready,
        },
    }
