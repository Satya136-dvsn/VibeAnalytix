"""
Integration tests for complete pipeline.
Tests end-to-end job execution.
"""

import tempfile
from pathlib import Path

import pytest

from app.parser import parse_repository
from app.analysis import run_analysis
from app.knowledge_builder import build_knowledge


@pytest.mark.asyncio
async def test_complete_pipeline_small_repo():
    """Test complete pipeline with small synthetic repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create test repository
        (tmppath / "main.py").write_text("""
def main():
    result = helper()
    return result

def helper():
    return 42

if __name__ == "__main__":
    main()
""")

        (tmppath / "utils.py").write_text("""
def format_output(value):
    return f"Result: {value}"

def parse_input(data):
    return int(data)
""")

        # Test parsing
        parsed_files = await parse_repository(tmppath)
        assert len(parsed_files) >= 2
        assert all(pf.path is not None for pf in parsed_files)

        # Test analysis
        analysis = await run_analysis(parsed_files, tmppath)
        assert analysis.file_tree is not None
        assert isinstance(analysis.dependency_graph, dict)

        # Test knowledge building
        knowledge = await build_knowledge(parsed_files, analysis)
        assert knowledge.function_summaries is not None
        assert knowledge.file_summaries is not None
        assert knowledge.module_summaries is not None
        assert knowledge.project_summary is not None


@pytest.mark.asyncio
async def test_pipeline_with_typescript():
    """Test pipeline with TypeScript code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create TypeScript files
        (tmppath / "index.ts").write_text("""
interface User {
  id: string
  name: string
}

function getUser(id: string): User {
  return { id, name: "John" }
}

export { getUser, User }
""")

        (tmppath / "api.ts").write_text("""
import { getUser, User } from "./index"

export async function fetchUser(id: string): Promise<User> {
  return getUser(id)
}
""")

        # Test parsing
        parsed_files = await parse_repository(tmppath)
        assert len(parsed_files) >= 2

        # Verify TypeScript language detection
        ts_files = [pf for pf in parsed_files if pf.language == "typescript"]
        assert len(ts_files) > 0

        # Test analysis
        analysis = await run_analysis(parsed_files, tmppath)
        assert analysis is not None


@pytest.mark.asyncio
async def test_pipeline_respects_language_limits():
    """Test parser respects file language limits."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create unsupported format
        (tmppath / "data.json").write_text('{"key": "value"}')

        # Create supported format
        (tmppath / "script.py").write_text("x = 1\ny = 2")

        # Test parsing
        parsed_files = await parse_repository(tmppath)

        # JSON should not be parsed (unsupported language)
        json_files = [pf for pf in parsed_files if "json" in pf.path]
        assert len(json_files) == 0

        # Python should be parsed
        py_files = [pf for pf in parsed_files if "py" in pf.path]
        assert len(py_files) > 0
