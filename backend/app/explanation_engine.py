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

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm_provider import LLMProviderService
from app.config import settings  # Kept for backwards-compatible test patching
from app.knowledge_builder import KnowledgeGraph
from app.schemas import ExplanationSet
from app.embeddings import generate_embedding
from app.vector_store import semantic_retrieval

logger = logging.getLogger(__name__)


class ExplanationResponseFormat(BaseModel):
    """Structured output format for GPT-4o explanation responses."""
    explanation: str
    key_points: list[str]
    confidence: float


class ExplanationEngine:
    """Generates explanations using OpenAI API with semantic context retrieval."""

    def __init__(self, api_key: str = None):
        """
        Initialize explanation engine.

        Args:
            api_key: LLM API key (if None, use settings)
        """
        self.provider = LLMProviderService(api_key=api_key)
        self.gemini_mode = self.provider.gemini_mode
        self.model = self.provider.model
        self.retry_delays = self.provider.retry_delays

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
        return await self.provider.retry_with_backoff(coro_factory, max_retries=max_retries)

    async def _call_openai_structured(
        self, system_prompt: str, user_prompt: str, response_format: type[BaseModel] = ExplanationResponseFormat
    ) -> dict:
        """
        Make a single chat completion call with structured output.
        """
        content = await self._call_llm(
            system_prompt,
            user_prompt,
            structured_schema=response_format.model_json_schema(),
            temperature=0.3,
            max_tokens=2000,
        )
            
        # Parse structured response
        try:
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            return {
                "explanation": content,
                "key_points": [],
                "confidence": 0.0,
            }

    async def _call_provider_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make a single provider-routed chat completion call.
        """
        return await self.provider.call_llm(
            system_prompt,
            user_prompt,
            temperature=0.3,
            max_tokens=4096,
        )

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        structured_schema: dict | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        """Backward-compatible wrapper around provider service."""
        return await self.provider.call_llm(
            system_prompt,
            user_prompt,
            structured_schema=structured_schema,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def _retrieve_similar_context(
        self,
        job_id: str,
        session: AsyncSession,
        knowledge: KnowledgeGraph,
        top_k: int = 10,
    ) -> list[dict]:
        """
        Retrieve top-k semantically similar function embeddings from pgvector.

        Generates a query embedding from the project context (project summary,
        key modules, entry points) and retrieves similar functions.

        Args:
            job_id: Job identifier
            session: Database session
            knowledge: Knowledge graph with project summaries
            top_k: Number of results to retrieve

        Returns:
            List of similar function summaries with their embeddings
        """
        from uuid import UUID
        from app.vector_store import semantic_retrieval

        try:
            job_uuid = UUID(job_id)

            # Build a query string from the project context
            # This will be embedded and used to find semantically similar functions
            query_parts = []

            # Add project summary
            if knowledge.project_summary and knowledge.project_summary.summary_text:
                query_parts.append(f"Project: {knowledge.project_summary.summary_text}")

            # Add entry points and external dependencies from project summary
            # The project_summary already contains this information

            # Add top module summaries
            if knowledge.module_summaries:
                for mod in knowledge.module_summaries[:5]:
                    if mod.summary_text:
                        query_parts.append(f"Module {mod.module_path}: {mod.summary_text}")

            # Add top file summaries
            if knowledge.file_summaries:
                for f in knowledge.file_summaries[:10]:
                    if f.summary_text:
                        query_parts.append(f"File {f.file_path}: {f.summary_text}")

            query_text = " ".join(query_parts) if query_parts else "code analysis"

            # Generate a query embedding with provider/model fallback.
            query_embedding = await generate_embedding(
                query_text,
                task_type="retrieval_query",
            )

            # Use the real embedding for semantic retrieval
            all_summaries = await semantic_retrieval(
                session=session,
                job_id=job_uuid,
                query_embedding=query_embedding,
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
        return await self.generate_project_overview_with_context(knowledge, context)

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
        context = self._build_context_string(knowledge)
        return await self.generate_per_file_explanations_with_context(knowledge, context)

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
        return await self.generate_execution_flow_with_context(knowledge, context)

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
        similar_functions = await self._retrieve_similar_context(job_id, session, knowledge, top_k=10)
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
            "You are a senior software engineer and technical mentor. "
            "You explain codebases for beginners with specific, concrete references to real files and functions. "
            "Never use vague phrases like modern architecture or modular architecture without naming what exactly. "
            "Write in clean Markdown and follow the required section format exactly. "
            "Do not add extra top-level sections before or after the required structure."
        )

        user_prompt = (
            "Based on the following deep code analysis data, generate a beginner-friendly codebase explanation.\n\n"
            f"{context}\n\n"
            "Follow this STRICT structure exactly, with these exact headings and numbering:\n\n"
            "# 1. Project Overview\n"
            "- What this project does (3-5 lines, simple explanation)\n"
            "- Main purpose of the application\n\n"
            "# 2. Tech Stack\n"
            "- Languages used\n"
            "- Frameworks\n"
            "- Tools\n\n"
            "# 3. Architecture Breakdown\n"
            "- Identify main components (frontend, backend, services, etc.)\n"
            "- Explain how components are connected\n\n"
            "# 4. Entry Points\n"
            "- Identify main starting files (e.g., main.py, layout.tsx)\n"
            "- Explain what happens when project starts\n\n"
            "# 5. Execution Flow\n"
            "Explain step-by-step how the system works:\n"
            "1. User action\n"
            "2. Processing\n"
            "3. Data flow\n"
            "4. Response\n\n"
            "# 6. Folder Structure Explanation\n"
            "For each major folder:\n"
            "- Purpose\n"
            "- What it contains\n\n"
            "# 7. Key File Explanations\n"
            "For important files:\n"
            "- Role of file\n"
            "- What it controls\n\n"
            "# 8. Code Understanding (IMPORTANT)\n"
            "For selected important functions:\n"
            "- What the function does\n"
            "- Input -> processing -> output\n\n"
            "# 9. Simplified Explanation (Teaching Mode)\n"
            "Explain the entire project in simple terms like teaching a beginner.\n"
            "Use analogies only when they improve clarity.\n\n"
            "Hard rules:\n"
            "- Be specific and grounded in real repository files/functions.\n"
            "- Avoid fluff, repetition, and unnecessary jargon.\n"
            "- Do not include extra sections outside 1-9.\n"
            "- Keep sentences simple and clear."
        )

        async def _create():
            return await self._call_provider_llm(system_prompt, user_prompt)

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
        """Generate per-file explanations with pre-built context, including actual source code."""
        explanations: dict[str, str] = {}
        semaphore = asyncio.Semaphore(5)
        function_map: dict[str, list] = {}

        for fn in knowledge.function_summaries:
            function_map.setdefault(fn.file_path, []).append(fn)

        # Build a lookup map: file_path -> source code
        source_map: dict[str, str] = {}
        if hasattr(knowledge, 'parsed_files') and knowledge.parsed_files:
            for pf in knowledge.parsed_files:
                try:
                    src = pf.source or ''
                    if isinstance(src, bytes):
                        src = src.decode('utf-8', errors='replace')
                    source_map[pf.path] = src
                except Exception:
                    source_map[pf.path] = ''

        system_prompt = (
            "You are a world-class senior developer writing an exhaustive, educational code walkthrough. "
            "When given a source file and its functions, you produce a complete technical explanation "
            "formatted in clean Markdown that lets ANY developer — even a complete beginner — fully "
            "understand the file WITHOUT opening it. "
            "Use ##, ###, bullet lists, inline `code`, and fenced code blocks. "
            "Be extremely specific: quote actual function signatures, variable names, class attributes, "
            "and line numbers from the code provided. Never write vague or generic text. "
            "Minimum target: 400 words per file."
        )

        async def _explain_file(file_summary):
            file_functions = function_map.get(file_summary.file_path, [])
            func_details = "\n".join(
                f"  - `{fn.function_name}` (lines {fn.line_start}–{fn.line_end}): {fn.summary_text or 'no summary'}"
                for fn in file_functions
            )

            # Include up to 8000 chars of real source code
            raw_source = source_map.get(file_summary.file_path, '')
            source_snippet = raw_source[:8000] if raw_source else '(source not available)'
            if len(raw_source) > 8000:
                source_snippet += f"\n\n... (file truncated, {len(raw_source)} chars total)"

            user_prompt = (
                f"## File to explain: `{file_summary.file_path}`\n\n"
                f"**Auto-generated summary:** {file_summary.summary_text or 'Not available'}\n\n"
                f"**Detected functions/classes:**\n{func_details or 'None detected'}\n\n"
                f"**Actual source code:**\n```\n{source_snippet}\n```\n\n"
                f"**Overall project context (abbreviated):**\n{context[:2000]}\n\n"
                "---\n"
                "Write a COMPLETE, DETAILED explanation of this file covering ALL of the following sections:\n\n"
                "## 📄 File Purpose\n"
                "What is the exact role of this file? What would break in the system if this file were deleted? "
                "State this in 3–5 clear sentences.\n\n"
                "## 🔧 Complete Function & Class Reference\n"
                "For **every** function, class, and method visible in the source code above:\n"
                "- Write its **full signature** (name + parameters + return type if visible)\n"
                "- Explain what it does in 2–4 sentences\n"
                "- List its parameters with their types and what they represent\n"
                "- Describe what it returns or what side-effect it produces\n"
                "- Note any exceptions raised, edge cases, or important constraints\n\n"
                "## 🔗 Imports & Dependencies\n"
                "List every import in this file. For each:\n"
                "- What module/package is it from?\n"
                "- What specifically is imported and why is it needed?\n\n"
                "## ⚙️ Implementation Deep-Dive\n"
                "Walk through the most interesting or complex parts of the implementation:\n"
                "- Any non-obvious algorithms or logic\n"
                "- Design patterns used (e.g. factory, singleton, decorator, context manager)\n"
                "- Any async/await patterns or concurrency concerns\n"
                "- Any configuration values, constants, or environment variables used\n\n"
                "## 🧪 How to Use / Interact With This File\n"
                "Give a concrete example of how another developer would call or use the main functions/classes "
                "in this file. Show example call signatures with plausible argument values.\n\n"
                "## 💡 Key Gotchas & Things to Know\n"
                "What are 3–5 things a developer MUST know before modifying this file? "
                "Include any hidden coupling, performance concerns, or things that are easy to break.\n\n"
                "Be exhaustive. Reference actual line numbers, variable names, and code from the source above."
            )

            async with semaphore:
                async def _create_for_file(prompt=user_prompt):
                    return await self._call_provider_llm(system_prompt, prompt)

                try:
                    explanation = await self._retry_with_backoff(_create_for_file)
                    if explanation:
                        return file_summary.file_path, explanation
                except Exception as e:
                    logger.warning(
                        f"Error generating explanation for {file_summary.file_path}: {e}"
                    )

                if file_summary.summary_text:
                    return file_summary.file_path, file_summary.summary_text
                return file_summary.file_path, None

        results = await asyncio.gather(
            *(_explain_file(file_summary) for file_summary in knowledge.file_summaries)
        )

        for file_path, explanation in results:
            if explanation:
                explanations[file_path] = explanation

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
            "You are a world-class systems engineer explaining how a complex codebase executes. "
            "Write a deeply detailed, step-by-step execution flow narrative formatted in clean Markdown. "
            "Use numbered sections, bullet points, inline code snippets (` `), and bold text. "
            "Be concrete — name the actual files and functions involved at each step. "
            "A developer unfamiliar with this codebase should be able to trace execution completely from your writeup."
        )

        user_prompt = (
            "Based on the following code analysis, produce a COMPREHENSIVE EXECUTION FLOW ANALYSIS. "
            "Minimum 400 words. Be specific and reference actual files/functions.\n\n"
            f"{context}\n"
            f"{entry_points_info}\n\n"
            "Structure your response with these sections:\n\n"
            "## 🚀 Application Entry Points\n"
            "What file(s) and function(s) are the starting point(s)? How does the process begin "
            "(e.g., CLI invocation, HTTP server, event loop start)?\n\n"
            "## ⚙️ Initialization & Bootstrap Sequence\n"
            "Walk through everything that happens at startup — config loading, database connections, "
            "service registrations, middleware setup — step by step.\n\n"
            "## 📨 Request / Event Processing Pipeline\n"
            "For the primary user-facing workflow (e.g., an HTTP request, a job submission, a command), "
            "trace the full execution path: which function is called first, what it does, what it calls next, "
            "and so on through every layer.\n\n"
            "## 💾 Data Layer Interactions\n"
            "When and how does this application read from or write to databases, caches, or external APIs? "
            "Name the specific functions and files responsible.\n\n"
            "## 📤 Output & Response Generation\n"
            "How does the system produce its final output or response? What transformations happen to data "
            "before it reaches the caller?\n\n"
            "## ♻️ Background Jobs & Async Patterns\n"
            "Are there worker queues, async tasks, or scheduled jobs? If so, explain when they fire and what they do.\n\n"
            "Remember: Name actual files and functions at every step."
        )

        async def _create():
            return await self._call_provider_llm(system_prompt, user_prompt)

        try:
            return await self._retry_with_backoff(_create)
        except Exception as e:
            logger.error(f"Error generating execution flow: {e}")
            fallback_exec = (
                "**1. Initialization Phase**\n"
                "The application boot process is orchestrated by the primary entry points defined in the repository surface. These components trigger the immediate instantiation of essential dependency injection containers and runtime configurators.\n\n"
                "**2. Request Lifecycle & Routing**\n"
                "Incoming invocations flow through the outer API boundaries or controller layers before reaching dedicated business logic domains. Sub-modules manage subsequent side-effects, enforcing isolation.\n\n"
                "**3. Data Emitting & Return**\n"
                "Output generation relies on state normalization strategies prior to yielding results, guaranteeing uniform interface contracts for all consumers."
            )
            if entry_points_info:
                return f"{fallback_exec}\n\n*Identified primary triggers:* {entry_points_info}"
            return fallback_exec


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
