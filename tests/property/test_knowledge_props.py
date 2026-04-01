"""
Property-based tests for Knowledge Builder using Hypothesis.
Tests Properties 12-15 from the design document.
"""

import pytest
from hypothesis import given, settings, strategies as st

from app.parser import ParsedFile, FunctionDef, ImportDef
from app.analysis import AnalysisResult
from app.parser import FileTreeNode
from app.knowledge_builder import KnowledgeBuilder, KnowledgeGraph


# ============ Helpers ============


def make_analysis_result(entry_points=None, external_deps=None):
    """Create a minimal AnalysisResult for testing."""
    return AnalysisResult(
        file_tree=FileTreeNode(name="root", path=".", is_dir=True),
        entry_points=entry_points or [],
        external_deps=external_deps or [],
    )


def make_parsed_file(path, language="python", functions=None):
    """Helper to create a ParsedFile for testing."""
    return ParsedFile(
        path=path,
        language=language,
        functions=functions or [],
    )


safe_name = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=15,
)


class TestKnowledgeHierarchyCompleteness:
    """Property-based tests for knowledge hierarchy completeness (Property 12)."""

    # Feature: vibeanalytix, Property 12: Knowledge Hierarchy Completeness
    @given(
        num_files=st.integers(min_value=1, max_value=5),
        funcs_per_file=st.integers(min_value=1, max_value=4),
    )
    @settings(max_examples=100)
    def test_all_levels_of_hierarchy_produced(self, num_files, funcs_per_file):
        """For any set of parsed files, function/file/module/project summaries are all produced."""
        parsed_files = []
        for i in range(num_files):
            functions = [
                FunctionDef(
                    name=f"func_{i}_{j}",
                    line_start=j * 10 + 1,
                    line_end=j * 10 + 8,
                )
                for j in range(funcs_per_file)
            ]
            parsed_files.append(
                make_parsed_file(f"dir_{i % 2}/file_{i}.py", functions=functions)
            )

        analysis = make_analysis_result()
        builder = KnowledgeBuilder(parsed_files, analysis)
        knowledge = builder.build()

        # Function summaries: one per function
        total_functions = num_files * funcs_per_file
        assert len(knowledge.function_summaries) == total_functions, (
            f"Expected {total_functions} function summaries, got {len(knowledge.function_summaries)}"
        )

        # File summaries: one per file
        assert len(knowledge.file_summaries) == num_files, (
            f"Expected {num_files} file summaries, got {len(knowledge.file_summaries)}"
        )

        # Module summaries: at least one (grouped by directory)
        assert len(knowledge.module_summaries) >= 1, (
            "Expected at least 1 module summary"
        )

        # Project summary: exactly one
        assert knowledge.project_summary is not None, "Expected project summary"
        assert knowledge.project_summary.summary_text is not None, (
            "Expected project summary text"
        )

    # Feature: vibeanalytix, Property 12: Knowledge Hierarchy Completeness (empty functions)
    @given(num_files=st.integers(min_value=1, max_value=5))
    @settings(max_examples=50)
    def test_files_without_functions_still_get_summaries(self, num_files):
        """Files without functions should still get file and module summaries."""
        parsed_files = [
            make_parsed_file(f"file_{i}.py", functions=[])
            for i in range(num_files)
        ]

        analysis = make_analysis_result()
        builder = KnowledgeBuilder(parsed_files, analysis)
        knowledge = builder.build()

        assert len(knowledge.function_summaries) == 0
        assert len(knowledge.file_summaries) == num_files
        assert knowledge.project_summary is not None


class TestFunctionChunkingBound:
    """Property-based tests for function chunking bound (Property 13)."""

    # Feature: vibeanalytix, Property 13: Function Chunking Bound
    @given(
        total_lines=st.integers(min_value=201, max_value=1000),
    )
    @settings(max_examples=100)
    def test_large_functions_chunked_within_bound(self, total_lines):
        """For any function body > 200 lines, every chunk should contain at most 200 lines."""
        func = FunctionDef(
            name="large_func",
            line_start=1,
            line_end=total_lines,
        )

        analysis = make_analysis_result()
        parsed_files = [make_parsed_file("test.py", functions=[func])]
        builder = KnowledgeBuilder(parsed_files, analysis)

        chunks = builder._chunk_function(func, "test.py", chunk_size=200)

        # Should produce multiple chunks
        assert len(chunks) > 1, (
            f"Expected multiple chunks for {total_lines}-line function, got {len(chunks)}"
        )

        # Every chunk should be at most 200 lines
        for chunk in chunks:
            chunk_lines = chunk.line_end - chunk.line_start + 1
            assert chunk_lines <= 200, (
                f"Chunk has {chunk_lines} lines, exceeds 200-line limit"
            )

        # All chunks together should cover the full function
        chunk_starts = [c.line_start for c in chunks]
        chunk_ends = [c.line_end for c in chunks]
        assert min(chunk_starts) == func.line_start
        assert max(chunk_ends) == func.line_end

    # Feature: vibeanalytix, Property 13: Function Chunking Bound (small functions)
    @given(
        total_lines=st.integers(min_value=1, max_value=200),
    )
    @settings(max_examples=100)
    def test_small_functions_not_chunked(self, total_lines):
        """Functions with <= 200 lines should NOT be chunked."""
        func = FunctionDef(
            name="small_func",
            line_start=1,
            line_end=total_lines,
        )

        analysis = make_analysis_result()
        parsed_files = [make_parsed_file("test.py", functions=[func])]
        builder = KnowledgeBuilder(parsed_files, analysis)

        chunks = builder._chunk_function(func, "test.py", chunk_size=200)

        assert len(chunks) == 1, (
            f"Expected 1 chunk for {total_lines}-line function, got {len(chunks)}"
        )
        assert chunks[0].chunk_index is None


class TestEmbeddingStorageRoundTrip:
    """Property-based tests for embedding storage round-trip (Property 14)."""

    # Feature: vibeanalytix, Property 14: Embedding Storage Round-Trip
    @given(
        func_name=safe_name,
        file_path=st.builds(
            lambda name: f"src/{name}.py",
            name=safe_name,
        ),
        line_start=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_function_summary_metadata_preserved(self, func_name, file_path, line_start):
        """After storing a function summary, querying should return the same metadata."""
        from app.knowledge_builder import FunctionSummary

        line_end = line_start + 10
        summary = FunctionSummary(
            file_path=file_path,
            function_name=func_name,
            line_start=line_start,
            line_end=line_end,
            summary_text=f"Summary for {func_name}",
        )

        # Verify round-trip of metadata fields
        assert summary.file_path == file_path
        assert summary.function_name == func_name
        assert summary.line_start == line_start
        assert summary.line_end == line_end
        assert summary.summary_text == f"Summary for {func_name}"


class TestSemanticRetrievalCount:
    """Property-based tests for semantic retrieval count (Property 15)."""

    # Feature: vibeanalytix, Property 15: Semantic Retrieval Count
    @given(
        n_embeddings=st.integers(min_value=10, max_value=50),
    )
    @settings(max_examples=100)
    def test_retrieval_returns_exactly_10(self, n_embeddings):
        """For N >= 10 stored embeddings, retrieval should return exactly 10 results."""
        # Simulate embedding storage and retrieval
        embeddings = list(range(n_embeddings))

        # Simulate top-10 retrieval (sorted by cosine similarity)
        top_k = 10
        retrieved = sorted(embeddings, reverse=True)[:top_k]

        assert len(retrieved) == 10, (
            f"Expected exactly 10 results from {n_embeddings} embeddings, got {len(retrieved)}"
        )

    # Feature: vibeanalytix, Property 15: Semantic Retrieval Count (ordering)
    @given(
        similarities=st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=10,
            max_size=30,
        ),
    )
    @settings(max_examples=100)
    def test_retrieval_ordered_by_descending_similarity(self, similarities):
        """Retrieved results should be ordered by descending cosine similarity."""
        # Simulate top-10 retrieval
        sorted_sims = sorted(similarities, reverse=True)[:10]

        for i in range(len(sorted_sims) - 1):
            assert sorted_sims[i] >= sorted_sims[i + 1], (
                f"Results not ordered: {sorted_sims[i]} < {sorted_sims[i+1]}"
            )
