"""
Property-based tests for Analysis Engine using Hypothesis.
Tests Properties 9-11 from the design document.
"""

import pytest
from hypothesis import given, settings, strategies as st

from app.parser import ParsedFile, FunctionDef, ImportDef, ClassDef
from app.analysis import AnalysisEngine, AnalysisResult


# ============ Strategies ============

safe_name = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_",
    min_size=1,
    max_size=15,
)


def make_parsed_file(path, language="python", imports=None, functions=None):
    """Helper to create a ParsedFile for testing."""
    return ParsedFile(
        path=path,
        language=language,
        imports=imports or [],
        functions=functions or [],
    )


class TestDependencyGraphCompleteness:
    """Property-based tests for dependency graph completeness (Property 9)."""

    # Feature: vibeanalytix, Property 9: Dependency Graph Completeness
    @given(
        num_files=st.integers(min_value=2, max_value=6),
    )
    @settings(max_examples=100)
    def test_all_import_relationships_in_graph(self, num_files):
        """For any set of files with imports, every import should appear as a graph edge."""
        # Create files where file_i imports file_0
        files = []
        for i in range(num_files):
            path = f"module_{i}.py"
            imports = []
            if i > 0:
                # File i imports file 0
                imports.append(ImportDef(module=f"module_0", is_external=False))
            files.append(make_parsed_file(path, imports=imports))

        # Run analysis
        engine = AnalysisEngine()
        dep_graph, _, _ = engine._pass_2_dependency_detection(files)

        # Every file that imports module_0 should have an edge to it
        for i in range(1, num_files):
            src = f"module_{i}.py"
            assert src in dep_graph, f"File {src} missing from dependency graph"
            # The dependency should reference the target file
            deps = dep_graph[src]
            assert any("module_0" in d for d in deps), (
                f"File {src} should depend on module_0, got {deps}"
            )

    # Feature: vibeanalytix, Property 9: Dependency Graph Completeness (all files present)
    @given(
        num_files=st.integers(min_value=1, max_value=8),
    )
    @settings(max_examples=100)
    def test_all_files_present_in_graph(self, num_files):
        """Every parsed file should have an entry in the dependency graph."""
        files = [
            make_parsed_file(f"file_{i}.py")
            for i in range(num_files)
        ]

        engine = AnalysisEngine()
        dep_graph, _, _ = engine._pass_2_dependency_detection(files)

        for f in files:
            assert f.path in dep_graph, f"File {f.path} missing from graph"


class TestCircularDependencyDetection:
    """Property-based tests for circular dependency detection (Property 10)."""

    # Feature: vibeanalytix, Property 10: Circular Dependency Detection
    @given(
        cycle_size=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=100)
    def test_cycles_are_detected(self, cycle_size):
        """For any dependency graph with a cycle, the cycle should be in the output."""
        # Build a cycle: file_0 -> file_1 -> ... -> file_n -> file_0
        dep_graph = {}
        for i in range(cycle_size):
            src = f"file_{i}.py"
            dst = f"file_{(i + 1) % cycle_size}.py"
            dep_graph[src] = [dst]

        engine = AnalysisEngine()
        cycles = engine._detect_circular_dependencies(dep_graph)

        # At least one cycle should be detected
        assert len(cycles) > 0, (
            f"Expected cycle detection for graph {dep_graph}, got none"
        )

    # Feature: vibeanalytix, Property 10: Circular Dependency Detection (no false positives)
    @given(
        chain_length=st.integers(min_value=2, max_value=6),
    )
    @settings(max_examples=100)
    def test_no_false_positives_for_linear_chains(self, chain_length):
        """For a linear chain (no cycles), no cycles should be detected."""
        # file_0 -> file_1 -> ... -> file_n (no cycle)
        dep_graph = {}
        for i in range(chain_length):
            src = f"file_{i}.py"
            if i < chain_length - 1:
                dst = f"file_{i + 1}.py"
                dep_graph[src] = [dst]
            else:
                dep_graph[src] = []

        engine = AnalysisEngine()
        cycles = engine._detect_circular_dependencies(dep_graph)

        assert len(cycles) == 0, (
            f"False positive: detected cycles {cycles} in linear chain"
        )


class TestExternalDependencyCompleteness:
    """Property-based tests for external dependency completeness (Property 11)."""

    # Feature: vibeanalytix, Property 11: External Dependency Completeness
    @given(
        external_modules=st.lists(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz_",
                min_size=2,
                max_size=15,
            ),
            min_size=1,
            max_size=8,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_all_external_imports_cataloged(self, external_modules):
        """For any files with known external imports, all should appear in external deps."""
        # Create files with external imports
        imports = [
            ImportDef(module=mod, is_external=True)
            for mod in external_modules
        ]
        files = [make_parsed_file("main.py", imports=imports)]

        engine = AnalysisEngine()
        _, _, external_deps = engine._pass_2_dependency_detection(files)

        # Every external module should be cataloged
        for mod in external_modules:
            assert mod in external_deps, (
                f"External dependency '{mod}' not found in {external_deps}"
            )

    # Feature: vibeanalytix, Property 11: External Dependency Completeness (no internal leakage)
    @given(
        num_internal=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100)
    def test_internal_imports_not_in_external(self, num_internal):
        """Internal imports should NOT appear in the external dependencies list."""
        files = []
        for i in range(num_internal):
            path = f"module_{i}.py"
            imports = []
            if i > 0:
                imports.append(ImportDef(module=f"module_{i-1}", is_external=False))
            files.append(make_parsed_file(path, imports=imports))

        engine = AnalysisEngine()
        _, _, external_deps = engine._pass_2_dependency_detection(files)

        for i in range(num_internal):
            for dep in external_deps:
                assert f"module_{i}" not in dep, (
                    f"Internal module 'module_{i}' leaked into external deps: {external_deps}"
                )
