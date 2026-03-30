"""
Explanation Engine generating AI-powered explanations using OpenAI.

Generates:
1. Project overview (purpose, architecture, key technologies)
2. Per-file explanations (role, key functions, relationships)
3. Execution flow (how program starts, processes input, produces output)
"""

import asyncio
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge_builder import KnowledgeGraph
from app.schemas import ExplanationSet
from app.config import settings

# In production, use: from openai import AsyncOpenAI
# For now we'll use a mock implementation


class ExplanationEngine:
    """Generates explanations using OpenAI API."""

    def __init__(self, api_key: str = settings.openai_api_key):
        """
        Initialize explanation engine.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        # self.client = AsyncOpenAI(api_key=api_key)  # In production

    async def _retry_with_backoff(
        self, coro, max_retries: int = 3
    ) -> Optional[str]:
        """
        Retry operation with exponential backoff.

        Args:
            coro: Coroutine to retry
            max_retries: Maximum number of retries

        Returns:
            Result or None if all retries fail
        """
        delays = [1, 2, 4]  # seconds

        for attempt in range(max_retries):
            try:
                return await coro()
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(delays[attempt])
                    continue
                # Final attempt failed
                raise

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

        async def create_overview():
            # In production, call OpenAI API
            # For now, generate based on available data
            if knowledge.project_summary:
                return knowledge.project_summary.summary_text or "Project overview"
            return "Project overview based on code analysis"

        try:
            return await self._retry_with_backoff(create_overview)
        except Exception as e:
            print(f"Error generating project overview: {e}")
            return None

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

        for file_summary in knowledge.file_summaries:
            async def create_file_explanation():
                # In production, call OpenAI API with file context
                # For now, use the available summary
                if file_summary.summary_text:
                    return file_summary.summary_text
                return f"Explanation for {file_summary.file_path}"

            try:
                explanation = await self._retry_with_backoff(create_file_explanation)
                if explanation:
                    explanations[file_summary.file_path] = explanation
            except Exception as e:
                print(f"Error generating explanation for {file_summary.file_path}: {e}")
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

        async def create_flow():
            # In production, call OpenAI API
            # For now, generate based on entry points
            entry_points = []
            if hasattr(knowledge, "analysis") and hasattr(knowledge.analysis, "entry_points"):
                entry_points = knowledge.analysis.entry_points

            if entry_points:
                return f"Execution flow starting from: {', '.join(entry_points)}"
            return "Execution flow analysis"

        try:
            return await self._retry_with_backoff(create_flow)
        except Exception as e:
            print(f"Error generating execution flow: {e}")
            return None

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
        # Generate all explanations concurrently
        overview_task = asyncio.create_task(
            self.generate_project_overview(knowledge)
        )
        per_file_task = asyncio.create_task(
            self.generate_per_file_explanations(knowledge)
        )
        flow_task = asyncio.create_task(
            self.generate_execution_flow(knowledge)
        )

        # Wait for all tasks
        overview = await overview_task
        per_file_explanations = await per_file_task
        flow = await flow_task

        return ExplanationSet(
            project_summary=knowledge.project_summary.summary_text if knowledge.project_summary else None,
            overview_explanation=overview,
            per_file_explanations=per_file_explanations,
            flow_explanation=flow,
        )


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
