"""
Knowledge Builder for hierarchical summarization and embedding generation.

Constructs:
1. Function-level summaries (with chunking for functions > 200 lines)
2. File-level summaries (aggregate of function summaries)
3. Module-level summaries (per directory)
4. Project-level summary (aggregate of all modules)
"""

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis import AnalysisResult
from app.parser import ParsedFile, FunctionDef


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


class KnowledgeBuilder:
    """Builds hierarchical knowledge graph from parsed code."""

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

    def build_function_summaries(self) -> list[FunctionSummary]:
        """
        Build function-level summaries with chunking support.

        Returns:
            List of FunctionSummary objects
        """
        summaries = []

        for parsed_file in self.parsed_files:
            if not parsed_file.functions:
                continue

            for func in parsed_file.functions:
                # Chunk function if needed
                func_summaries = self._chunk_function(func, parsed_file.path)
                summaries.extend(func_summaries)

        return summaries

    def build_file_summaries(self) -> list[FileSummary]:
        """
        Build file-level summaries by aggregating function summaries.

        Returns:
            List of FileSummary objects
        """
        summaries = []
        file_function_map: dict[str, list[FunctionSummary]] = {}

        # Group function summaries by file
        for func_summary in self.function_summaries:
            if func_summary.file_path not in file_function_map:
                file_function_map[func_summary.file_path] = []
            file_function_map[func_summary.file_path].append(func_summary)

        # Create file summaries
        for parsed_file in self.parsed_files:
            file_summary = FileSummary(
                file_path=parsed_file.path,
                functions=file_function_map.get(parsed_file.path, []),
            )
            # Generate summary text from function summaries
            if file_summary.functions:
                func_names = ", ".join(
                    f.function_name for f in file_summary.functions
                )
                file_summary.summary_text = (
                    f"File {parsed_file.path} containing functions: {func_names}"
                )

            summaries.append(file_summary)

        return summaries

    def build_module_summaries(self) -> list[ModuleSummary]:
        """
        Build module-level summaries by directory.

        Returns:
            List of ModuleSummary objects
        """
        summaries = []
        module_file_map: dict[str, list[FileSummary]] = {}

        # Group files by directory (module)
        for file_summary in self.file_summaries:
            # Extract directory from file path
            parts = file_summary.file_path.split("/")
            module_path = "/".join(parts[:-1]) if len(parts) > 1 else "."

            if module_path not in module_file_map:
                module_file_map[module_path] = []
            module_file_map[module_path].append(file_summary)

        # Create module summaries
        for module_path, files in sorted(module_file_map.items()):
            file_names = ", ".join(f.file_path.split("/")[-1] for f in files)
            module_summary = ModuleSummary(
                module_path=module_path,
                files=files,
                summary_text=f"Module {module_path} containing files: {file_names}",
            )
            summaries.append(module_summary)

        return summaries

    def build_project_summary(self) -> ProjectSummary:
        """
        Build project-level summary.

        Returns:
            ProjectSummary object
        """
        # Extract key information
        num_files = len(self.parsed_files)
        num_functions = len(self.function_summaries)
        languages = set(pf.language for pf in self.parsed_files if pf.language)
        entry_points = self.analysis.entry_points
        external_deps = self.analysis.external_deps

        summary_parts = [
            f"Project with {num_files} files",
            f"containing {num_functions} functions",
            f"in {', '.join(sorted(languages))}",
            f"with entry points: {', '.join(entry_points) or 'None'}",
            f"external dependencies: {', '.join(external_deps[:5]) or 'None'}",
        ]

        summary_text = ". ".join(summary_parts) + "."

        return ProjectSummary(
            summary_text=summary_text,
            modules=self.module_summaries,
        )

    def build(self) -> KnowledgeGraph:
        """
        Build complete knowledge graph.

        Returns:
            Complete KnowledgeGraph
        """
        # Build in order (bottom-up)
        self.function_summaries = self.build_function_summaries()
        self.file_summaries = self.build_file_summaries()
        self.module_summaries = self.build_module_summaries()
        project_summary = self.build_project_summary()

        return KnowledgeGraph(
            function_summaries=self.function_summaries,
            file_summaries=self.file_summaries,
            module_summaries=self.module_summaries,
            project_summary=project_summary,
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
    return builder.build()


async def generate_and_store_embeddings(
    job_id: str,
    knowledge: KnowledgeGraph,
    session: AsyncSession,
) -> None:
    """
    Generate embeddings for function summaries and store in pgvector.

    Args:
        job_id: Job identifier
        knowledge: Knowledge graph with summaries
        session: Database session

    Note:
        Placeholder implementation. Will integrate with OpenAI API.
    """
    # TODO: Implement OpenAI embedding generation
    # For now, this is a placeholder
    pass
