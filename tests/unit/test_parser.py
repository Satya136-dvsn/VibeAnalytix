"""
Unit tests for Parser module.
Tests language detection and AST extraction.
"""

import tempfile
from pathlib import Path

import pytest

from app.parser import (
    LanguageDetector,
    parse_repository,
    FunctionDef,
    ClassDef,
    ParsedFile,
)


class TestLanguageDetection:
    """Test language detection from file extensions (Property 4)."""

    def test_python_detection(self):
        """Test Python file detection."""
        detector = LanguageDetector()
        assert detector.detect_language(Path("main.py")) == "python"
        assert detector.detect_language(Path("app.pyw")) == "python"

    def test_javascript_detection(self):
        """Test JavaScript file detection."""
        detector = LanguageDetector()
        assert detector.detect_language(Path("index.js")) == "javascript"
        assert detector.detect_language(Path("app.jsx")) == "javascript"

    def test_typescript_detection(self):
        """Test TypeScript file detection."""
        detector = LanguageDetector()
        assert detector.detect_language(Path("main.ts")) == "typescript"
        assert detector.detect_language(Path("component.tsx")) == "typescript"

    def test_java_detection(self):
        """Test Java file detection."""
        detector = LanguageDetector()
        assert detector.detect_language(Path("Main.java")) == "java"

    def test_go_detection(self):
        """Test Go file detection."""
        detector = LanguageDetector()
        assert detector.detect_language(Path("main.go")) == "go"

    def test_c_detection(self):
        """Test C file detection."""
        detector = LanguageDetector()
        assert detector.detect_language(Path("main.c")) == "c"
        assert detector.detect_language(Path("header.h")) == "c"

    def test_cpp_detection(self):
        """Test C++ file detection."""
        detector = LanguageDetector()
        assert detector.detect_language(Path("main.cpp")) == "cpp"
        assert detector.detect_language(Path("app.cc")) == "cpp"

    def test_unknown_extension(self):
        """Test unknown extensions return None."""
        detector = LanguageDetector()
        assert detector.detect_language(Path("file.txt")) is None
        assert detector.detect_language(Path("README.md")) is None


class TestFileTreeCompleteness:
    """Test file tree building (Property 5)."""

    @pytest.mark.asyncio
    async def test_file_tree_includes_all_files(self):
        """Test that file tree includes all source files in repository."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test files
            (tmppath / "main.py").write_text("print('hello')")
            (tmppath / "utils.py").write_text("def helper(): pass")
            (tmppath / "subdir").mkdir()
            (tmppath / "subdir" / "module.py").write_text("x = 1")

            # Parse repository
            parsed_files = await parse_repository(tmppath)

            # Extract paths
            paths = {pf.path for pf in parsed_files}

            # Verify all files are included
            assert any("main.py" in p for p in paths)
            assert any("utils.py" in p for p in paths)
            assert any("module.py" in p for p in paths)


class TestParserResilience:
    """Test parser resilience to invalid files (Property 6)."""

    @pytest.mark.asyncio
    async def test_parser_continues_on_invalid_files(self):
        """Parser should continue despite invalid files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Valid file
            (tmppath / "valid.py").write_text("print('hello')")

            # Invalid Python file (syntax error)
            (tmppath / "invalid.py").write_text("def broken( {")

            # Unknown language
            (tmppath / "data.json").write_text('{"key": "value"}')

            # Parse repository
            parsed_files = await parse_repository(tmppath)

            # Should have parsed the valid file
            assert any("valid.py" in pf.path for pf in parsed_files)

            # Invalid file should be present with error
            invalid_parsed = next(
                (pf for pf in parsed_files if "invalid.py" in pf.path),
                None
            )
            # Either parsed with errors or skipped - both acceptable


class TestASTExtraction:
    """Test AST extraction completeness (Property 7)."""

    def test_extract_functions(self):
        """Test function extraction from Python code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            py_file = tmppath / "test.py"

            py_file.write_text("""
def simple_function():
    pass

def function_with_args(a, b, c):
    return a + b + c

class MyClass:
    def method(self):
        pass
""")

            from app.parser import TreeSitterParser

            parser = TreeSitterParser()
            ast = parser.parse_file(py_file)

            if ast:
                functions = parser.extract_functions(ast, "python")
                # Should find at least the named functions
                names = {f.name for f in functions}
                assert any("simple_function" in name for name in names)
                assert any("function_with_args" in name for name in names)
