"""
Explanation Engine generating AI-powered explanations using OpenAI.

Generates:
1. Project overview (purpose, architecture, key technologies)
2. Per-file explanations (role, key functions, relationships)
3. Execution flow (how program starts, processes input, produces output)

Uses semantic retrieval via pgvector to build context-aware prompts.
"""

import asyncio
import json
import logging
from typing import Optional

from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge_builder import KnowledgeGraph
from app.schemas import ExplanationSet
from app.config import settings
from app.vector_store import semantic_retrieval

logger = logging.getLogger(__name__)


class ExplanationResponseFormat(BaseModel):
    """Structured output format for GPT-4o explanation responses."""
    explanation: str
    key_points: list[str]
    confidence: float


class ExplanationEngine:
    """Generates explanations using OpenAI API with semantic context retrieval."""

    # Retryable OpenAI errors
    RETRYABLE_ERRORS = (APIError, RateLimitError, APIConnectionError)

    def __init__(self, api_key: str = settings.openai_api_key):
        """
        Initialize explanation engine.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o"
        self.retry_delays = [1, 2, 4]  # Exponential backoff seconds
        self.max_retries = 3

    async def _retry_with_backoff(
        self, coro_factory, max_retries: int = 3
    ) -> Optional[str]:
        """
        Retry operation with exponential backoff.

        Args:
            coro_factory: Callable that returns a coroutine to retry
            max_retries: Maximum number of retries

        Returns:
            Result or None if all retries fail

        Raises:
            Exception: If all retries are exhausted
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                return await coro_factory()
            except self.RETRYABLE_ERRORS as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.warning(
                        f"OpenAI API error (attempt {attempt + 1}/{max_retries}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                # Final attempt failed
                logger.error(
                    f"OpenAI API call failed after {max_retries} attempts: {e}"
                )
                raise
            except Exception as e:
                # Non-retryable error, raise immediately
                raise

    async def _call_openai_structured(
        self, system_prompt: str, user_prompt: str, response_format: type[BaseModel] = ExplanationResponseFormat
    ) -> str:
        """
        Make a single OpenAI chat completion call with structured output.

        Args:
            system_prompt: System role message
            user_prompt: User role message
            response_format: Pydantic model for structured output

        Returns:
            Generated text response
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object", "schema": response_format.model_json_schema()},
            temperature=0.3,
            max_tokens=2000,
        )
        # Parse structured response
        content = response.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
            return parsed.get("explanation", content)
        except json.JSONDecodeError:
            return content

    async def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make a single OpenAI chat completion call.

        Args:
            system_prompt: System role message
            user_prompt: User role message

        Returns:
            Generated text response
        """
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return response.choices[0].message.content or ""

    async def _retrieve_similar_context(
        self,
        job_id: str,
        session: AsyncSession,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Retrieve top-k semantically similar function embeddings from pgvector.

        Args:
            job_id: Job identifier
            session: Database session
            top_k: Number of results to retrieve

        Returns:
            List of similar function summaries with their embeddings
        """
        from uuid import UUID
        from app.vector_store import semantic_retrieval

        try:
            job_uuid = UUID(job_id)

            # Generate a dummy query embedding for context retrieval
            # In practice, we'd use a query-specific embedding, but for
            # general context we retrieve the most "representative" functions
            all_summaries = await semantic_retrieval(
                session=session,
                job_id=job_uuid,
                query_embedding=[0.0] * 1536,  # Dummy - would be replaced by actual query
                top_k=top_k,
            )

            return [
                {
                    "file_path": s.file_path,
                    "function_name": s.function_name,
                    "line_start": s.line_start,
                    "line_end": s.line_end,
                    "summary_text": s.summary_text,
                }
                for s in all_summaries
            ]
        except Exception as e:
            logger.warning(f"Semantic retrieval failed: {e}")
            return []

    def _build_context_string(self, knowledge: KnowledgeGraph, similar_functions: list[dict] = None) -> str:
        """
        Build a context string from the knowledge graph for prompt construction.

        Args:
            knowledge: Knowledge graph with summaries

        Returns:
            Context string for LLM prompts
        """
        parts = []

        # Project-level context
        if knowledge.project_summary and knowledge.project_summary.summary_text:
            parts.append(f"## Project Summary\n{knowledge.project_summary.summary_text}")

        # Module-level context
        if knowledge.module_summaries:
            module_lines = []
            for ms in knowledge.module_summaries:
                if ms.summary_text:
                    module_lines.append(f"- **{ms.module_path}**: {ms.summary_text}")
            if module_lines:
                parts.append("## Modules\n" + "\n".join(module_lines))

        # File-level context
        if knowledge.file_summaries:
            file_lines = []
            for fs in knowledge.file_summaries[:20]:  # Limit to top 20 files
                if fs.summary_text:
                    file_lines.append(f"- **{fs.file_path}**: {fs.summary_text}")
            if file_lines:
                parts.append("## Key Files\n" + "\n".join(file_lines))

        # Function-level context (top 30 functions)
        if knowledge.function_summaries:
            func_lines = []
            for fn in knowledge.function_summaries[:30]:
                func_lines.append(
                    f"- `{fn.function_name}` in {fn.file_path} "
                    f"(lines {fn.line_start}-{fn.line_end})"
                )
            if func_lines:
                parts.append("## Key Functions\n" + "\n".join(func_lines))

        # Semantically retrieved context (top-10 from pgvector)
        if similar_functions:
            sim_lines = []
            for sf in similar_functions:
                sim_lines.append(
                    f"- `{sf['function_name']}` in {sf['file_path']} "
                    f"(lines {sf['line_start']}-{sf['line_end']}): {sf.get('summary_text', '')}"
                )
            if sim_lines:
                parts.append("## Semantically Similar Functions (from codebase)\n" + "\n".join(sim_lines))

        return "\n\n".join(parts)

    async def generate_project_overview(
        self, knowledge: KnowledgeGraph
    ) -> Optional[str]:
        """
        Generate project overview explanation.

        Args:
            knowledge: Knowledge graph

        Returns:
            Project overview explanation or None on failure
        """
        context = self._build_context_string(knowledge)

        system_prompt = (
            "You are a code documentation expert. Generate a clear, structured, "
            "beginner-friendly project overview. Include: purpose, architecture, "
            "key technologies, and how the components fit together. "
            "Write in plain English at a level understandable by an entry-level developer."
        )

        user_prompt = (
            "Based on the following code analysis, generate a comprehensive project overview:\n\n"
            f"{context}\n\n"
            "Include sections for:\n"
            "1. Project Purpose - What does this project do?\n"
            "2. Architecture - How is the code organized?\n"
            "3. Key Technologies - What languages, frameworks, and libraries are used?\n"
            "4. Key Components - What are the main modules and their responsibilities?"
        )

        async def _create():
            return await self._call_openai(system_prompt, user_prompt)

        try:
            return await self._retry_with_backoff(_create)
        except Exception as e:
            logger.error(f"Error generating project overview: {e}")
            # Fallback to knowledge-graph-based summary
            if knowledge.project_summary and knowledge.project_summary.summary_text:
                return knowledge.project_summary.summary_text
            return "Project overview could not be generated."

    async def generate_per_file_explanations(
        self, knowledge: KnowledgeGraph
    ) -> dict[str, str]:
        """
        Generate per-file explanations.

        Args:
            knowledge: Knowledge graph

        Returns:
            Dictionary mapping file paths to explanations
        """
        explanations: dict[str, str] = {}
        context = self._build_context_string(knowledge)

        system_prompt = (
            "You are a code documentation expert. Generate a clear, "
            "beginner-friendly explanation for a specific source file. "
            "Describe its role in the project, key functions/classes, "
            "and relationships to other files. "
            "Write in plain English at a level understandable by an entry-level developer."
        )

        for file_summary in knowledge.file_summaries:
            # Build file-specific context
            file_functions = [
                fn for fn in knowledge.function_summaries
                if fn.file_path == file_summary.file_path
            ]
            func_list = "\n".join(
                f"  - `{fn.function_name}` (lines {fn.line_start}-{fn.line_end})"
                for fn in file_functions
            )

            user_prompt = (
                f"Generate an explanation for the file: **{file_summary.file_path}**\n\n"
                f"File summary: {file_summary.summary_text or 'N/A'}\n\n"
                f"Functions in this file:\n{func_list or 'No functions detected'}\n\n"
                f"Project context:\n{context[:2000]}\n\n"  # Truncate context
                "Explain:\n"
                "1. What this file does\n"
                "2. Key functions and their purposes\n"
                "3. How it relates to other parts of the project"
            )

            async def _create_for_file(prompt=user_prompt):
                return await self._call_openai(system_prompt, prompt)

            try:
                explanation = await self._retry_with_backoff(_create_for_file)
                if explanation:
                    explanations[file_summary.file_path] = explanation
            except Exception as e:
                logger.warning(
                    f"Error generating explanation for {file_summary.file_path}: {e}"
                )
                # Use fallback summary
                if file_summary.summary_text:
                    explanations[file_summary.file_path] = file_summary.summary_text
                continue

        return explanations

    async def generate_execution_flow(
        self, knowledge: KnowledgeGraph
    ) -> Optional[str]:
        """
        Generate execution flow explanation.

        Args:
            knowledge: Knowledge graph

        Returns:
            Execution flow explanation or None on failure
        """
        context = self._build_context_string(knowledge)

        # Extract entry points from analysis if available
        entry_points_info = ""
        if hasattr(knowledge, "analysis") and hasattr(knowledge.analysis, "entry_points"):
            entry_points = knowledge.analysis.entry_points
            if entry_points:
                entry_points_info = f"\nIdentified entry points: {', '.join(entry_points)}"

        system_prompt = (
            "You are a code documentation expert. Generate a clear, "
            "beginner-friendly execution flow narrative. Explain how the program "
            "starts, what happens step by step, how it processes input, and how "
            "it produces output. Write as a narrative that an entry-level developer "
            "can follow."
        )

        user_prompt = (
            f"Based on the following code analysis, describe the execution flow:\n\n"
            f"{context}\n"
            f"{entry_points_info}\n\n"
            "Describe:\n"
            "1. How the program starts (entry point)\n"
            "2. The initialization sequence\n"
            "3. How user input/requests are processed\n"
            "4. How data flows through the system\n"
            "5. How output is produced"
        )

        async def _create():
            return await self._call_openai(system_prompt, user_prompt)

        try:
            return await self._retry_with_backoff(_create)
        except Exception as e:
            logger.error(f"Error generating execution flow: {e}")
            # Fallback
            if entry_points_info:
                return f"Execution flow starting from: {entry_points_info}"
            return "Execution flow analysis could not be generated."

    async def generate_explanations(
        self,
        job_id: str,
        knowledge: KnowledgeGraph,
        session: AsyncSession,
    ) -> ExplanationSet:
        """
        Generate complete explanation set.

        Args:
            job_id: Job identifier
            knowledge: Knowledge graph
            session: Database session

        Returns:
            Complete ExplanationSet
        """
        logger.info(f"Generating explanations for job {job_id}")

        # First: retrieve semantically similar functions from pgvector
        similar_functions = await self._retrieve_similar_context(job_id, session, top_k=10)
        logger.info(f"Retrieved {len(similar_functions)} semantically similar functions")

        # Build context with semantic retrieval
        context = self._build_context_string(knowledge, similar_functions)

        # Generate all explanations concurrently (passing shared context)
        overview_task = asyncio.create_task(
            self.generate_project_overview_with_context(knowledge, context)
        )
        per_file_task = asyncio.create_task(
            self.generate_per_file_explanations_with_context(knowledge, context)
        )
        flow_task = asyncio.create_task(
            self.generate_execution_flow_with_context(knowledge, context)
        )

        # Wait for all tasks
        overview = await overview_task
        per_file_explanations = await per_file_task
        flow = await flow_task

        logger.info(
            f"Explanations generated for job {job_id}: "
            f"overview={'yes' if overview else 'no'}, "
            f"files={len(per_file_explanations)}, "
            f"flow={'yes' if flow else 'no'}"
        )

        return ExplanationSet(
            project_summary=knowledge.project_summary.summary_text if knowledge.project_summary else None,
            overview_explanation=overview,
            per_file_explanations=per_file_explanations,
            flow_explanation=flow,
        )

    async def generate_project_overview_with_context(
        self, knowledge: KnowledgeGraph, context: str
    ) -> Optional[str]:
        """Generate project overview with pre-built context."""
        system_prompt = (
            "You are a code documentation expert. Generate a clear, structured, "
            "beginner-friendly project overview. Include: purpose, architecture, "
            "key technologies, and how the components fit together. "
            "Write in plain English at a level understandable by an entry-level developer."
        )

        user_prompt = (
            "Based on the following code analysis, generate a comprehensive project overview:\n\n"
            f"{context}\n\n"
            "Include sections for:\n"
            "1. Project Purpose - What does this project do?\n"
            "2. Architecture - How is the code organized?\n"
            "3. Key Technologies - What languages, frameworks, and libraries are used?\n"
            "4. Key Components - What are the main modules and their responsibilities?"
        )

        async def _create():
            return await self._call_openai_structured(system_prompt, user_prompt)

        try:
            return await self._retry_with_backoff(_create)
        except Exception as e:
            logger.error(f"Error generating project overview: {e}")
            if knowledge.project_summary and knowledge.project_summary.summary_text:
                return knowledge.project_summary.summary_text
            return "Project overview could not be generated."

    async def generate_per_file_explanations_with_context(
        self, knowledge: KnowledgeGraph, context: str
    ) -> dict[str, str]:
        """Generate per-file explanations with pre-built context."""
        explanations: dict[str, str] = {}

        system_prompt = (
            "You are a code documentation expert. Generate a clear, "
            "beginner-friendly explanation for a specific source file. "
            "Describe its role in the project, key functions/classes, "
            "and relationships to other files. "
            "Write in plain English at a level understandable by an entry-level developer."
        )

        for file_summary in knowledge.file_summaries:
            file_functions = [
                fn for fn in knowledge.function_summaries
                if fn.file_path == file_summary.file_path
            ]
            func_list = "\n".join(
                f"  - `{fn.function_name}` (lines {fn.line_start}-{fn.line_end})"
                for fn in file_functions
            )

            user_prompt = (
                f"Generate an explanation for the file: **{file_summary.file_path}**\n\n"
                f"File summary: {file_summary.summary_text or 'N/A'}\n\n"
                f"Functions in this file:\n{func_list or 'No functions detected'}\n\n"
                f"Project context:\n{context[:2000]}\n\n"
                "Explain:\n"
                "1. What this file does\n"
                "2. Key functions and their purposes\n"
                "3. How it relates to other parts of the project"
            )

            async def _create_for_file(prompt=user_prompt):
                return await self._call_openai_structured(system_prompt, prompt)

            try:
                explanation = await self._retry_with_backoff(_create_for_file)
                if explanation:
                    explanations[file_summary.file_path] = explanation
            except Exception as e:
                logger.warning(
                    f"Error generating explanation for {file_summary.file_path}: {e}"
                )
                if file_summary.summary_text:
                    explanations[file_summary.file_path] = file_summary.summary_text
                continue

        return explanations

    async def generate_execution_flow_with_context(
        self, knowledge: KnowledgeGraph, context: str
    ) -> Optional[str]:
        """Generate execution flow with pre-built context."""
        entry_points_info = ""
        if hasattr(knowledge, "analysis") and hasattr(knowledge.analysis, "entry_points"):
            entry_points = knowledge.analysis.entry_points
            if entry_points:
                entry_points_info = f"\nIdentified entry points: {', '.join(entry_points)}"

        system_prompt = (
            "You are a code documentation expert. Generate a clear, "
            "beginner-friendly execution flow narrative. Explain how the program "
            "starts, what happens step by step, how it processes input, and how "
            "it produces output. Write as a narrative that an entry-level developer "
            "can follow."
        )

        user_prompt = (
            f"Based on the following code analysis, describe the execution flow:\n\n"
            f"{context}\n"
            f"{entry_points_info}\n\n"
            "Describe:\n"
            "1. How the program starts (entry point)\n"
            "2. The initialization sequence\n"
            "3. How user input/requests are processed\n"
            "4. How data flows through the system\n"
            "5. How output is produced"
        )

        async def _create():
            return await self._call_openai_structured(system_prompt, user_prompt)

        try:
            return await self._retry_with_backoff(_create)
        except Exception as e:
            logger.error(f"Error generating execution flow: {e}")
            if entry_points_info:
                return f"Execution flow starting from: {entry_points_info}"
            return "Execution flow analysis could not be generated."


async def generate_explanations(
    job_id: str,
    knowledge: KnowledgeGraph,
    session: AsyncSession,
) -> ExplanationSet:
    """
    Generate complete explanation set for a job.

    Args:
        job_id: Job identifier
        knowledge: Knowledge graph
        session: Database session

    Returns:
        Complete ExplanationSet
    """
    engine = ExplanationEngine()
    return await engine.generate_explanations(job_id, knowledge, session)
