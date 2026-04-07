"""
LLM provider routing and retry logic for text generation.
"""

import asyncio
import os

import google.generativeai as genai
from openai import AsyncOpenAI, APIConnectionError, APIError, RateLimitError

from app.config import settings


class LLMProviderService:
    """Provider abstraction for Gemini/OpenAI text generation."""

    RETRYABLE_ERRORS = (APIError, RateLimitError, APIConnectionError)

    @staticmethod
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

    def __init__(self, api_key: str | None = None):
        is_pytest = "PYTEST_CURRENT_TEST" in os.environ

        has_gemini_key = self._is_configured_key(
            settings.gemini_api_key, expected_prefix="AIza"
        ) and not is_pytest
        has_openai_key = self._is_configured_key(settings.openai_api_key, expected_prefix="sk-") and not is_pytest
        has_runtime_openai_key = self._is_configured_key(api_key, expected_prefix="sk-") and not is_pytest

        self.gemini_mode = has_gemini_key
        self.gemini_model = None
        self.client = None
        self.model = settings.gemini_text_model if self.gemini_mode else "gpt-4o"

        if has_gemini_key:
            genai.configure(api_key=settings.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(settings.gemini_text_model)

        openai_key = settings.openai_api_key or ""
        if has_runtime_openai_key:
            openai_key = api_key
        if has_runtime_openai_key or has_openai_key:
            self.client = AsyncOpenAI(api_key=openai_key)
            if not self.gemini_mode:
                self.model = "gpt-4o"

        self.retry_delays = [1, 2, 4]

    async def retry_with_backoff(self, coro_factory, max_retries: int = 3):
        """Retry coroutine execution with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await coro_factory()
            except self.RETRYABLE_ERRORS:
                if attempt < max_retries - 1:
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue
                raise

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        structured_schema: dict | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Route text generation to available providers with fallback."""
        if self.client is not None:
            openai_system_prompt = system_prompt
            if structured_schema is not None:
                openai_system_prompt = f"{system_prompt}\n\nRespond with valid JSON only."

            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": openai_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if structured_schema is not None:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "explanation_response",
                        "schema": structured_schema,
                    },
                }

            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""

        if self.gemini_mode and self.gemini_model is not None:
            prompt = f"{system_prompt}\n\n{user_prompt}"
            generation_kwargs = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            if structured_schema is not None:
                prompt = (
                    f"{prompt}\n\nPlease respond in valid JSON matching this schema: "
                    f"{structured_schema}"
                )
                generation_kwargs = {
                    "response_mime_type": "application/json",
                }
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(**generation_kwargs),
            )
            return response.text

        raise RuntimeError("No LLM provider configured for text generation")
