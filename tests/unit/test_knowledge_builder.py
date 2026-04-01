"""
Unit tests for Knowledge Builder.
Tests chunking logic, aggregation hierarchy, and embedding retry behavior.
"""

import pytest

from app.parser import ParsedFile, FunctionDef, ImportDef
from app.analysis import AnalysisResult
from app.parser import FileTreeNode
from app.knowledge_builder import (
    KnowledgeBuilder,
    KnowledgeGraph,
    FunctionSummary,
    FileSummary,
    ModuleSummary,
    ProjectSummary,
)


def make_analysis_result(entry_points=None, external_deps=None):
    """Create a minimal AnalysisResult."""
    return AnalysisResult(
        file_tree=FileTreeNode(name="root", path=".", is_dir=True),
        entry_points=entry_points or [],
        external_deps=external_deps or [],
    )


class TestFunctionChunking:
    """Test function body chunking logic."""

    def test_small_function_not_chunked(self):
        """Functions <= 200 lines should not be chunked."""
        func = FunctionDef(name="small", line_start=1, line_end=50)
        analysis = make_analysis_result()
        parsed_files = [ParsedFile(path="test.py", language="python", functions=[func])]
        builder = KnowledgeBuilder(parsed_files, analysis)

        chunks = builder._chunk_function(func, "test.py")

        assert len(chunks) == 1
        assert chunks[0].function_name == "small"
        assert chunks[0].chunk_index is None

    def test_exactly_200_lines_not_chunked(self):
        """A function with exactly 200 lines should not be chunked."""
        func = FunctionDef(name="exact", line_start=1, line_end=200)
        analysis = make_analysis_result()
        parsed_files = [ParsedFile(path="test.py", language="python", functions=[func])]
        builder = KnowledgeBuilder(parsed_files, analysis)

        chunks = builder._chunk_function(func, "test.py")

        assert len(chunks) == 1

    def test_201_lines_produces_two_chunks(self):
        """A function with 201 lines should produce 2 chunks."""
        func = FunctionDef(name="big", line_start=1, line_end=201)
        analysis = make_analysis_result()
        parsed_files = [ParsedFile(path="test.py", language="python", functions=[func])]
        builder = KnowledgeBuilder(parsed_files, analysis)

        chunks = builder._chunk_function(func, "test.py")

        assert len(chunks) == 2
        # First chunk: lines 1-200
        assert chunks[0].line_start == 1
        assert chunks[0].line_end == 200
        # Second chunk: line 201
        assert chunks[1].line_start == 201
        assert chunks[1].line_end == 201

    def test_400_lines_produces_two_chunks(self):
        """A function with 400 lines should produce 2 chunks of 200 each."""
        func = FunctionDef(name="large", line_start=1, line_end=400)
        analysis = make_analysis_result()
        parsed_files = [ParsedFile(path="test.py", language="python", functions=[func])]
        builder = KnowledgeBuilder(parsed_files, analysis)

        chunks = builder._chunk_function(func, "test.py")

        assert len(chunks) == 2
        for chunk in chunks:
            chunk_size = chunk.line_end - chunk.line_start + 1
            assert chunk_size <= 200

    def test_chunk_names_include_index(self):
        """Chunked function names should include chunk index."""
        func = FunctionDef(name="chunked_func", line_start=1, line_end=500)
        analysis = make_analysis_result()
        parsed_files = [ParsedFile(path="test.py", language="python", functions=[func])]
        builder = KnowledgeBuilder(parsed_files, analysis)

        chunks = builder._chunk_function(func, "test.py")

        assert len(chunks) == 3
        assert "chunk_1" in chunks[0].function_name
        assert "chunk_2" in chunks[1].function_name
        assert "chunk_3" in chunks[2].function_name


class TestAggregationHierarchy:
    """Test hierarchical summary aggregation."""

    def test_function_summaries_generated(self):
        """Every function should get a summary."""
        funcs = [
            FunctionDef(name="func_a", line_start=1, line_end=10),
            FunctionDef(name="func_b", line_start=15, line_end=25),
        ]
        parsed_files = [ParsedFile(path="test.py", language="python", functions=funcs)]
        analysis = make_analysis_result()

        builder = KnowledgeBuilder(parsed_files, analysis)
        knowledge = builder.build()

        assert len(knowledge.function_summaries) == 2

    def test_file_summaries_generated(self):
        """Every file should get a file-level summary."""
        parsed_files = [
            ParsedFile(
                path="file_a.py",
                language="python",
                functions=[FunctionDef(name="func_a", line_start=1, line_end=10)],
            ),
            ParsedFile(
                path="file_b.py",
                language="python",
                functions=[FunctionDef(name="func_b", line_start=1, line_end=10)],
            ),
        ]
        analysis = make_analysis_result()

        builder = KnowledgeBuilder(parsed_files, analysis)
        knowledge = builder.build()

        assert len(knowledge.file_summaries) == 2

    def test_module_summaries_grouped_by_directory(self):
        """Files in the same directory should be grouped into one module."""
        parsed_files = [
            ParsedFile(
                path="src/file_a.py",
                language="python",
                functions=[FunctionDef(name="func_a", line_start=1, line_end=10)],
            ),
            ParsedFile(
                path="src/file_b.py",
                language="python",
                functions=[FunctionDef(name="func_b", line_start=1, line_end=10)],
            ),
        ]
        analysis = make_analysis_result()

        builder = KnowledgeBuilder(parsed_files, analysis)
        knowledge = builder.build()

        # Both files in "src/" directory → 1 module
        src_modules = [m for m in knowledge.module_summaries if m.module_path == "src"]
        assert len(src_modules) == 1
        assert len(src_modules[0].files) == 2

    def test_project_summary_generated(self):
        """A single project-level summary should be generated."""
        parsed_files = [
            ParsedFile(
                path="main.py",
                language="python",
                functions=[FunctionDef(name="main", line_start=1, line_end=10)],
            ),
        ]
        analysis = make_analysis_result(entry_points=["main.py"])

        builder = KnowledgeBuilder(parsed_files, analysis)
        knowledge = builder.build()

        assert knowledge.project_summary is not None
        assert knowledge.project_summary.summary_text is not None
        assert "main.py" in knowledge.project_summary.summary_text

    def test_project_summary_includes_languages(self):
        """Project summary should mention detected languages."""
        parsed_files = [
            ParsedFile(path="main.py", language="python", functions=[]),
            ParsedFile(path="app.js", language="javascript", functions=[]),
        ]
        analysis = make_analysis_result()

        builder = KnowledgeBuilder(parsed_files, analysis)
        knowledge = builder.build()

        assert "python" in knowledge.project_summary.summary_text.lower()
        assert "javascript" in knowledge.project_summary.summary_text.lower()

    def test_empty_files_still_counted(self):
        """Files without functions should still be counted in project summary."""
        parsed_files = [
            ParsedFile(path="empty.py", language="python", functions=[]),
        ]
        analysis = make_analysis_result()

        builder = KnowledgeBuilder(parsed_files, analysis)
        knowledge = builder.build()

        assert "1 files" in knowledge.project_summary.summary_text


class TestKnowledgeGraphDataclasses:
    """Test KnowledgeGraph dataclass behavior."""

    def test_knowledge_graph_defaults(self):
        """KnowledgeGraph should have sensible defaults."""
        kg = KnowledgeGraph()
        assert kg.function_summaries == []
        assert kg.file_summaries == []
        assert kg.module_summaries == []
        assert kg.project_summary is None

    def test_function_summary_fields(self):
        """FunctionSummary should store all required fields."""
        fs = FunctionSummary(
            file_path="test.py",
            function_name="test_func",
            line_start=1,
            line_end=10,
            summary_text="A test function",
            chunk_index=None,
        )
        assert fs.file_path == "test.py"
        assert fs.function_name == "test_func"
        assert fs.line_start == 1
        assert fs.line_end == 10

    def test_file_summary_contains_functions(self):
        """FileSummary should contain its function summaries."""
        func = FunctionSummary(
            file_path="test.py",
            function_name="func",
            line_start=1,
            line_end=5,
        )
        fs = FileSummary(
            file_path="test.py",
            functions=[func],
            summary_text="Test file",
        )
        assert len(fs.functions) == 1
        assert fs.functions[0].function_name == "func"
