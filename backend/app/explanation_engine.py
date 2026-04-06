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

import google.generativeai as genai
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

    def __init__(self, api_key: str = None):
        """
        Initialize explanation engine.

        Args:
            api_key: LLM API key (if None, use settings)
        """
        self.gemini_mode = bool(settings.gemini_api_key)
        
        if self.gemini_mode:
            self.api_key = api_key or settings.gemini_api_key
            genai.configure(api_key=self.api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
            self.client = None
            self.model = "gemini-2.0-flash"
        else:
            self.api_key = api_key or settings.openai_api_key
            self.client = AsyncOpenAI(api_key=self.api_key)
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
        Make a single chat completion call with structured output.
        """
        if self.gemini_mode:
            # Gemini structured call
            prompt = f"{system_prompt}\n\n{user_prompt}\n\nPlease respond in valid JSON matching this schema: {response_format.model_json_schema()}"
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
            )
            content = response.text
        else:
            # OpenAI structured call
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
            content = response.choices[0].message.content or ""
            
        # Parse structured response
        try:
            parsed = json.loads(content)
            return parsed.get("explanation", content)
        except json.JSONDecodeError:
            return content

    async def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make a single chat completion call.
        """
        if self.gemini_mode:
            prompt = f"{system_prompt}\n\n{user_prompt}"
            response = await self.gemini_model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.3, max_output_tokens=4096)
            )
            return response.text
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            return response.choices[0].message.content or ""

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

            # Generate a real query embedding from the project context
            if self.gemini_mode:
                response = await genai.embed_content_async(
                    model="models/text-embedding-004",
                    content=query_text[:8000],
                    task_type="retrieval_query",
                )
                query_embedding = response['embedding']
            else:
                response = await self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=query_text[:8000],  # Truncate to stay within token limits
                )
                query_embedding = response.data[0].embedding

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
            "You are a world-class senior software architect writing comprehensive technical documentation. "
            "Your goal is to produce a deeply detailed, easy-to-read, well-structured project report "
            "formatted in clean Markdown. Imagine you are explaining this codebase to a new developer "
            "who has never seen it before — every section should be crystal clear with zero ambiguity. "
            "Use headings (##, ###), bullet points, bold text, and code blocks (` `) liberally. "
            "Do NOT use raw asterisks as literal text — only use markdown formatting as proper syntax. "
            "Do NOT be vague or generic. Reference specific files, functions, and patterns you see in the data."
        )

        user_prompt = (
            "Based on the following deep code analysis data, produce a COMPREHENSIVE PROJECT REPORT. "
            "Be as detailed and specific as possible — minimum 600 words. \n\n"
            f"{context}\n\n"
            "Your report MUST include ALL of the following sections, in this order:\n\n"
            "## 🎯 Project Purpose & Problem Statement\n"
            "What real-world problem does this project solve? Who is the intended user? What is the core value proposition?\n\n"
            "## 🏗️ System Architecture\n"
            "Describe the overall architectural pattern (e.g., MVC, microservices, monolith, event-driven). "
            "What are the main layers and how do they communicate? Include a text-based architecture diagram if helpful.\n\n"
            "## 🛠️ Technology Stack\n"
            "List every language, framework, library, and tool detected. For each, briefly explain WHY it is used in this project.\n\n"
            "## 📁 Key Modules & Their Responsibilities\n"
            "For each significant module/directory, explain in 2-4 sentences what it does, what it owns, and "
            "how it interacts with the rest of the system. Reference specific files.\n\n"
            "## ⚙️ Core Functionality Breakdown\n"
            "List the top 5-8 most important features or behaviors of the system. For each feature, "
            "explain HOW the code implements it — name the key functions and files involved.\n\n"
            "## 🔗 Data Flow & Integration Points\n"
            "Trace how data enters, moves through, and exits the system. Where is state held? "
            "What APIs or databases are integrated?\n\n"
            "## ⚠️ Notable Patterns & Design Decisions\n"
            "Identify any interesting design patterns (factory, singleton, observer, etc.), "
            "unusual architectural choices, or things a new developer should pay special attention to.\n\n"
            "Remember: Be specific, reference actual files and functions from the data above, and write at minimum 600 words."
        )

        async def _create():
            return await self._call_openai(system_prompt, user_prompt)

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
            "You are a world-class senior developer writing crystal-clear technical documentation. "
            "For each source file, write a deeply detailed, structured explanation formatted in Markdown. "
            "Use headings (###), bullet points, inline code (` `), and bold text. "
            "Do NOT produce generic filler text — be specific and reference actual function names, "
            "class names, arguments, and line numbers from the data provided. "
            "A junior developer reading your documentation should understand exactly what this file "
            "does without opening it."
        )

        for file_summary in knowledge.file_summaries:
            file_functions = [
                fn for fn in knowledge.function_summaries
                if fn.file_path == file_summary.file_path
            ]
            func_details = "\n".join(
                f"  - `{fn.function_name}` (lines {fn.line_start}–{fn.line_end}): {fn.summary_text or 'no summary'}"
                for fn in file_functions
            )

            user_prompt = (
                f"Write a DETAILED EXPLANATION for the file: `{file_summary.file_path}`\n\n"
                f"**AI-generated file summary:** {file_summary.summary_text or 'Not available'}\n\n"
                f"**Functions & methods detected:**\n{func_details or 'None detected'}\n\n"
                f"**Overall project context:**\n{context[:3000]}\n\n"
                "Your explanation MUST include these sections:\n\n"
                "### 📄 File Overview\n"
                "In 3-5 sentences, explain this file's SPECIFIC role and responsibility within the project. "
                "Be concrete — what would break if this file didn't exist?\n\n"
                "### 🔧 Functions & Classes Explained\n"
                "For EACH function/class listed above, provide:\n"
                "- Its purpose in 1-2 sentences\n"
                "- What parameters it accepts and what it returns\n"
                "- Any important side effects, exceptions, or edge cases\n\n"
                "### 🔗 How It Connects\n"
                "Which other files/modules does this file import from or export to? "
                "What is its position in the call chain (e.g., called by X, calls Y)?\n\n"
                "### 💡 Key Implementation Details\n"
                "Highlight any non-obvious logic, important design decisions, or patterns a developer must know "
                "before modifying this file.\n\n"
                "Be specific — avoid generic phrases. Aim for at least 200 words."
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
            return await self._call_openai(system_prompt, user_prompt)

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
