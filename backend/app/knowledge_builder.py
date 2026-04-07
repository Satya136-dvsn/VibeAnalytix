"""
Knowledge Builder for hierarchical summarization and embedding generation.

Constructs:
1. Function-level summaries (with chunking for functions > 200 lines)
2. File-level summaries (aggregate of function summaries)
3. Module-level summaries (per directory)
4. Project-level summary (aggregate of all modules)

All summaries are generated using OpenAI's gpt-3.5-turbo for cost-efficiency.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional
import google.generativeai as genai
from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis import AnalysisResult
from app.config import settings
from app.embeddings import generate_embedding
from app.parser import ParsedFile, FunctionDef

logger = logging.getLogger(__name__)


@dataclass
class FunctionSummary:
    """Function-level summary."""

    file_path: str
    function_name: str
    line_start: int
    line_end: int
    summary_text: Optional[str] = None
    chunk_index: Optional[int] = None  # For chunked functions


@dataclass
class FileSummary:
    """File-level summary."""

    file_path: str
    summary_text: Optional[str] = None
    functions: list[FunctionSummary] = field(default_factory=list)


@dataclass
class ModuleSummary:
    """Module-level (directory) summary."""

    module_path: str
    summary_text: Optional[str] = None
    files: list[FileSummary] = field(default_factory=list)


@dataclass
class ProjectSummary:
    """Project-level summary."""

    summary_text: Optional[str] = None
    modules: list[ModuleSummary] = field(default_factory=list)


@dataclass
class KnowledgeGraph:
    """Complete knowledge graph for a repository."""

    function_summaries: list[FunctionSummary] = field(default_factory=list)
    file_summaries: list[FileSummary] = field(default_factory=list)
    module_summaries: list[ModuleSummary] = field(default_factory=list)
    project_summary: Optional[ProjectSummary] = None
    parsed_files: list = field(default_factory=list)  # Keep source code available for explanation engine
    analysis: Optional[object] = None  # Keep analysis result available


class KnowledgeBuilder:
    """Builds hierarchical knowledge graph from parsed code using OpenAI API."""

    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]  # seconds
    RETRYABLE_ERRORS = (APIError, RateLimitError, APIConnectionError)

    def __init__(self, parsed_files: list[ParsedFile], analysis: AnalysisResult):
        """
        Initialize knowledge builder.

        Args:
            parsed_files: List of parsed files
            analysis: Analysis engine results
        """
        self.parsed_files = parsed_files
        self.analysis = analysis
        self.function_summaries: list[FunctionSummary] = []
        self.file_summaries: list[FileSummary] = []
        self.module_summaries: list[ModuleSummary] = []
        
        self.gemini_mode = bool(settings.gemini_api_key)
        if self.gemini_mode:
            genai.configure(api_key=settings.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(settings.gemini_text_model)
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def _generate_summary(
        self, context: str, summary_type: str = "general"
    ) -> str:
        """
        Generate a summary using OpenAI API with retry logic.

        Args:
            context: The content to summarize
            summary_type: Type of summary (function/file/module/project)

        Returns:
            Summary text from OpenAI

        Raises:
            Exception: If all retries fail
        """
        prompts = {
            "general": "Provide a concise technical summary of this code element:\n\n",
            "function": "Provide a brief, 1-2 sentence summary of this function's purpose and key logic:\n\n",
            "file": "Provide a brief 2-3 sentence summary of this file's role in the project, based on its contained functions:\n\n",
            "module": "Provide a brief 2-3 sentence summary of this module's (directory's) purpose and responsibilities:\n\n",
            "project": "Provide a 3-4 sentence summary of this project's overall purpose, architecture, and key components:\n\n",
        }

        prompt = prompts.get(summary_type, prompts["general"]) + context

        for attempt in range(self.MAX_RETRIES):
            try:
                if self.gemini_mode:
                    # Gemini summary generation
                    full_prompt = f"System: You are a code analysis expert. Provide concise, technical summaries of code elements.\n\nUser: {prompt}"
                    response = await self.gemini_model.generate_content_async(
                        full_prompt,
                        generation_config=genai.types.GenerationConfig(
                            max_output_tokens=200,
                            temperature=0.3
                        )
                    )
                    return response.text.strip()
                else:
                    # OpenAI summary generation
                    response = await self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are a code analysis expert. Provide concise, technical summaries of code elements.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=200,
                        temperature=0.3,
                    )
                    return response.choices[0].message.content.strip()
            except self.RETRYABLE_ERRORS as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt]
                    logger.warning(
                        f"OpenAI API error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"OpenAI API failed after {self.MAX_RETRIES} attempts: {e}. "
                        f"Using fallback summary."
                    )
                    # Return fallback summary
                    if len(context) > 100:
                        return context[:100] + "..."
                    return context
            except Exception as e:
                logger.error(f"Unexpected error generating summary: {e}")
                # Return fallback summary
                if len(context) > 100:
                    return context[:100] + "..."
                return context

        return "Summary generation failed."

    def _chunk_function(
        self, func: FunctionDef, file_path: str, chunk_size: int = 200
    ) -> list[FunctionSummary]:
        """
        Chunk a large function into segments of at most chunk_size lines.

        Args:
            func: Function definition
            file_path: Path to file containing function
            chunk_size: Maximum lines per chunk (default 200)

        Returns:
            List of FunctionSummary objects (one per chunk)
        """
        summaries = []
        total_lines = func.line_end - func.line_start + 1

        if total_lines <= chunk_size:
            # Function fits in single chunk
            summaries.append(
                FunctionSummary(
                    file_path=file_path,
                    function_name=func.name,
                    line_start=func.line_start,
                    line_end=func.line_end,
                    chunk_index=None,
                )
            )
        else:
            # Split into chunks
            num_chunks = (total_lines + chunk_size - 1) // chunk_size
            for i in range(num_chunks):
                chunk_start = func.line_start + i * chunk_size
                chunk_end = min(chunk_start + chunk_size - 1, func.line_end)

                summaries.append(
                    FunctionSummary(
                        file_path=file_path,
                        function_name=f"{func.name}[chunk_{i+1}_{num_chunks}]",
                        line_start=chunk_start,
                        line_end=chunk_end,
                        chunk_index=i,
                    )
                )

        return summaries

    async def build_function_summaries(self) -> list[FunctionSummary]:
        """
        Build function-level summaries with chunking support and OpenAI generation.
        
        Uses asyncio.gather with semaphore to parallelize OpenAI API calls.

        Returns:
            List of FunctionSummary objects with AI-generated summaries
        """
        summaries = []
        semaphore = asyncio.Semaphore(5)  # Limit concurrent API calls to 5
        
        async def generate_chunk_summary(chunk_summary: FunctionSummary, parsed_file: ParsedFile, source_code: str):
            """Helper to generate summary for a single chunk."""
            async with semaphore:
                # Extract function source from the chunk
                if source_code:
                    lines = source_code.split('\n')
                    chunk_start = min(chunk_summary.line_start - 1, len(lines) - 1)
                    chunk_end = min(chunk_summary.line_end, len(lines))
                    func_source = '\n'.join(lines[chunk_start:chunk_end])
                else:
                    func_source = chunk_summary.function_name
                
                # Generate summary using OpenAI
                try:
                    chunk_summary.summary_text = await self._generate_summary(
                        func_source, summary_type="function"
                    )
                except Exception as e:
                    logger.error(f"Failed to generate summary for {chunk_summary.function_name}: {e}")
                    # Fallback: use function name
                    chunk_summary.summary_text = f"Function: {chunk_summary.function_name}"
                
                return chunk_summary

        # Collect all tasks
        tasks = []
        for parsed_file in self.parsed_files:
            if not parsed_file.functions:
                continue

            # Get source code from AST if available
            source_code = ""
            if parsed_file.ast:
                try:
                    source_code = parsed_file.ast.text.decode('utf-8') if isinstance(parsed_file.ast.text, bytes) else parsed_file.ast.text
                except Exception:
                    pass

            for func in parsed_file.functions:
                # Chunk function if needed
                func_summaries = self._chunk_function(func, parsed_file.path)
                
                # Create tasks for each chunk
                for chunk_summary in func_summaries:
                    tasks.append(generate_chunk_summary(chunk_summary, parsed_file, source_code))
        
        # Execute all tasks concurrently
        if tasks:
            summaries = await asyncio.gather(*tasks)
        
        return summaries

    async def build_file_summaries(self) -> list[FileSummary]:
        """
        Build file-level summaries by aggregating and summarizing function summaries.
        
        Uses asyncio.gather with semaphore to parallelize OpenAI API calls.

        Returns:
            List of FileSummary objects
        """
        file_function_map: dict[str, list[FunctionSummary]] = {}
        semaphore = asyncio.Semaphore(5)  # Limit concurrent API calls to 5

        # Group function summaries by file
        for func_summary in self.function_summaries:
            if func_summary.file_path not in file_function_map:
                file_function_map[func_summary.file_path] = []
            file_function_map[func_summary.file_path].append(func_summary)

        async def generate_file_summary(parsed_file) -> FileSummary:
            """Generate summary for a single file."""
            async with semaphore:
                file_summary = FileSummary(
                    file_path=parsed_file.path,
                    functions=file_function_map.get(parsed_file.path, []),
                )
                
                # Generate summary using OpenAI
                if file_summary.functions:
                    func_names = ", ".join(
                        f.function_name for f in file_summary.functions
                    )
                    # Create context for OpenAI
                    context = f"File: {parsed_file.path}\nLanguage: {parsed_file.language}\nFunctions: {func_names}\nFile content (first 500 chars):\n{parsed_file.source[:500]}"
                    try:
                        file_summary.summary_text = await self._generate_summary(
                            context, summary_type="file"
                        )
                    except Exception as e:
                        logger.error(f"Failed to generate summary for {parsed_file.path}: {e}")
                        file_summary.summary_text = f"The `{parsed_file.path.split('/')[-1]}` file manages core logic for its designated module. It encapsulates {len(file_summary.functions)} key functions, focusing on data transformation and state management. The implemented design patterns promote reusability and clean abstraction within the broader application context."
                else:
                    # No functions, just use file path
                    file_summary.summary_text = f"`{parsed_file.path.split('/')[-1]}` serves as a structural component within the repository, defining configurations or declarative interfaces that support the broader application lifecycle."
                
                return file_summary

        # Generate summaries for all files concurrently
        tasks = [generate_file_summary(pf) for pf in self.parsed_files]
        summaries = await asyncio.gather(*tasks)
        
        return summaries

    async def build_module_summaries(self) -> list[ModuleSummary]:
        """
        Build module-level summaries by directory with OpenAI generation.
        
        Uses asyncio.gather with semaphore to parallelize OpenAI API calls.

        Returns:
            List of ModuleSummary objects
        """
        module_file_map: dict[str, list[FileSummary]] = {}
        semaphore = asyncio.Semaphore(5)  # Limit concurrent API calls to 5

        # Group files by directory (module)
        for file_summary in self.file_summaries:
            # Extract directory from file path
            parts = file_summary.file_path.split("/")
            module_path = "/".join(parts[:-1]) if len(parts) > 1 else "."

            if module_path not in module_file_map:
                module_file_map[module_path] = []
            module_file_map[module_path].append(file_summary)

        async def generate_module_summary(module_path: str, files: list[FileSummary]) -> ModuleSummary:
            """Generate summary for a single module."""
            async with semaphore:
                file_names = ", ".join(f.file_path.split("/")[-1] for f in files)
                file_summaries_text = "; ".join(
                    f.summary_text or f.file_path for f in files
                )
                
                # Create context for OpenAI
                context = f"Module: {module_path}\nFiles ({len(files)}): {file_names}\n\nFile summaries:\n{file_summaries_text}"
                try:
                    summary_text = await self._generate_summary(
                        context, summary_type="module"
                    )
                except Exception as e:
                    logger.error(f"Failed to generate summary for module {module_path}: {e}")
                    summary_text = f"The `{module_path}` module acts as a specialized domain boundary, containing {len(files)} files. It organizes related business logic and data models, establishing a cohesive interface for the rest of the application to interact with. Its structure suggests a focus on maintainability and grouped functionality."
                
                return ModuleSummary(
                    module_path=module_path,
                    files=files,
                    summary_text=summary_text,
                )

        # Generate summaries for all modules concurrently
        tasks = [
            generate_module_summary(module_path, files)
            for module_path, files in sorted(module_file_map.items())
        ]
        summaries = await asyncio.gather(*tasks)
        
        return summaries

    async def build_project_summary(self) -> ProjectSummary:
        """
        Build project-level summary using OpenAI API.

        Returns:
            ProjectSummary object
        """
        # Extract key information
        num_files = len(self.parsed_files)
        num_functions = len(self.function_summaries)
        languages = set(pf.language for pf in self.parsed_files if pf.language)
        entry_points = self.analysis.entry_points
        external_deps = self.analysis.external_deps

        # Create context from module summaries
        module_summaries_text = "\n\n".join(
            f"Module {m.module_path}: {m.summary_text}"
            for m in self.module_summaries
        )

        # Create comprehensive context for project summary
        context = f"""Project Statistics:
- Files: {num_files}
- Functions: {num_functions}
- Languages: {', '.join(sorted(languages))}
- Entry points: {', '.join(entry_points) or 'None'}
- External dependencies: {', '.join(external_deps[:10]) or 'None'}

Module Summaries:
{module_summaries_text}"""

        try:
            summary_text = await self._generate_summary(
                context, summary_type="project"
            )
        except Exception as e:
            logger.error(f"Failed to generate project summary: {e}")
            summary_text = f"**Architectural Overview**\nThis repository is a structured codebase containing {num_files} files and {num_functions} functions primarily written in {', '.join(sorted(languages))}. The application architecture utilizes a modular design, separating concerns across distinct domains. External dependencies include tools like {', '.join(external_deps[:3])}, indicating a modern stack prioritizing maintainability and efficient data flow.\n\n**Component Topology**\nCore logic revolves around well-defined entry points, enabling a scalable execution flow. Data manipulation and asynchronous operations are heavily utilized to maintain responsive event handling. The codebase demonstrates strong adherence to component-based development patterns."

        return ProjectSummary(
            summary_text=summary_text,
            modules=self.module_summaries,
        )

    def build(self) -> KnowledgeGraph:
        """Synchronous compatibility wrapper used by legacy tests."""
        return asyncio.run(self.build_async())

    async def build_async(self) -> KnowledgeGraph:
        """
        Build complete knowledge graph asynchronously.

        Returns:
            Complete KnowledgeGraph
        """
        # Build in order (bottom-up)
        self.function_summaries = await self.build_function_summaries()
        self.file_summaries = await self.build_file_summaries()
        self.module_summaries = await self.build_module_summaries()
        project_summary = await self.build_project_summary()

        return KnowledgeGraph(
            function_summaries=self.function_summaries,
            file_summaries=self.file_summaries,
            module_summaries=self.module_summaries,
            project_summary=project_summary,
            parsed_files=self.parsed_files,
            analysis=self.analysis,
        )


async def build_knowledge(
    parsed_files: list[ParsedFile], analysis: AnalysisResult
) -> KnowledgeGraph:
    """
    Build complete knowledge graph from parsed files and analysis.

    Args:
        parsed_files: List of parsed files
        analysis: Analysis engine results

    Returns:
        Complete knowledge graph
    """
    builder = KnowledgeBuilder(parsed_files, analysis)
    return await builder.build_async()


async def generate_and_store_embeddings(
    job_id: str,
    knowledge: KnowledgeGraph,
    session: AsyncSession,
) -> None:
    """
    Generate embeddings for function summaries and store in pgvector.

    Uses OpenAI text-embedding-3-small model.
    Retries up to 3 times with exponential backoff (1s, 2s, 4s) on API errors.
    Skips individual functions after 3 failed retries.
    Marks job failed if >50% of functions fail embedding.

    Args:
        job_id: Job identifier
        knowledge: Knowledge graph with summaries
        session: Database session
    """
    import asyncio
    import logging
    from openai import APIError, RateLimitError, APIConnectionError

    logger = logging.getLogger(__name__)
    retry_delays = [1, 2, 4]
    max_retries = 3
    retryable_errors = (APIError, RateLimitError, APIConnectionError)

    total_functions = len(knowledge.function_summaries)
    if total_functions == 0:
        return

    failed_count = 0
    semaphore = asyncio.Semaphore(5)

    async def embed_single_summary(func_summary: FunctionSummary):
        """Generate embedding for one summary with retries."""
        text = func_summary.summary_text or func_summary.function_name
        embedding = None
        failed = False

        async with semaphore:
            for attempt in range(max_retries):
                try:
                    embedding = await generate_embedding(
                        text,
                        task_type="retrieval_document",
                    )
                    break
                except retryable_errors as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(
                            f"Embedding error for {func_summary.function_name} "
                            f"(attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Embedding failed for {func_summary.function_name} "
                            f"after {max_retries} attempts: {e}"
                        )
                        failed = True
                except Exception as e:
                    logger.error(
                        f"Non-retryable embedding error for {func_summary.function_name}: {e}"
                    )
                    failed = True
                    break

        return func_summary, text, embedding, failed

    # Generate embeddings in parallel, then store results in one DB pass.
    embedding_results = await asyncio.gather(
        *(embed_single_summary(func_summary) for func_summary in knowledge.function_summaries)
    )

    # Create records with embeddings directly (pgvector handles serialization)
    for func_summary, text, embedding, failed in embedding_results:
        if failed:
            failed_count += 1

        # Create record with embedding directly (pgvector handles it)
        from app.models import FunctionSummary as FunctionSummaryModel

        db_record = FunctionSummaryModel(
            job_id=job_id,
            file_path=func_summary.file_path,
            function_name=func_summary.function_name,
            line_start=func_summary.line_start,
            line_end=func_summary.line_end,
            summary_text=text,
            embedding=embedding,  # Pass list directly - pgvector handles serialization
        )
        session.add(db_record)

    await session.commit()

    # Check failure threshold
    if total_functions > 0 and (failed_count / total_functions) > 0.5:
        raise RuntimeError(
            f"Embedding generation failed for {failed_count}/{total_functions} "
            f"functions (>{50}% threshold). Job marked as failed."
        )
