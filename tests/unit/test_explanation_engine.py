"""
Unit tests for Explanation Engine.
Tests specific scenarios for explanation generation.
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.knowledge_builder import (
    KnowledgeGraph,
    FunctionSummary,
    FileSummary,
    ModuleSummary,
    ProjectSummary,
)
from app.schemas import ExplanationSet


def make_test_knowledge():
    """Create a test KnowledgeGraph."""
    func1 = FunctionSummary(
        file_path="main.py",
        function_name="main",
        line_start=1,
        line_end=20,
        summary_text="Main entry point function",
    )
    func2 = FunctionSummary(
        file_path="utils.py",
        function_name="helper",
        line_start=1,
        line_end=10,
        summary_text="Helper utility function",
    )

    file1 = FileSummary(
        file_path="main.py",
        summary_text="Main application file",
        functions=[func1],
    )
    file2 = FileSummary(
        file_path="utils.py",
        summary_text="Utility functions module",
        functions=[func2],
    )

    return KnowledgeGraph(
        function_summaries=[func1, func2],
        file_summaries=[file1, file2],
        module_summaries=[
            ModuleSummary(
                module_path=".",
                summary_text="Root module",
                files=[file1, file2],
            )
        ],
        project_summary=ProjectSummary(
            summary_text="Test project with main and utils",
        ),
    )


class TestExplanationEngineInit:
    """Test ExplanationEngine initialization."""

    @patch("app.explanation_engine.settings")
    def test_engine_initializes_with_api_key(self, mock_settings):
        """Engine should initialize with API key from settings."""
        mock_settings.openai_api_key = "sk-test-key"
        from app.explanation_engine import ExplanationEngine

        engine = ExplanationEngine(api_key="sk-test-key")
        assert engine.api_key == "sk-test-key"
        assert engine.model == "gpt-4o"
        assert engine.max_retries == 3

    @patch("app.explanation_engine.settings")
    def test_retry_delays_are_exponential(self, mock_settings):
        """Retry delays should follow exponential backoff pattern."""
        mock_settings.openai_api_key = "sk-test-key"
        from app.explanation_engine import ExplanationEngine

        engine = ExplanationEngine(api_key="sk-test-key")
        assert engine.retry_delays == [1, 2, 4]
        for i in range(len(engine.retry_delays) - 1):
            assert engine.retry_delays[i + 1] > engine.retry_delays[i]


class TestContextBuilding:
    """Test prompt context construction."""

    @patch("app.explanation_engine.settings")
    def test_context_includes_project_summary(self, mock_settings):
        """Context string should include project summary."""
        mock_settings.openai_api_key = "sk-test-key"
        from app.explanation_engine import ExplanationEngine

        engine = ExplanationEngine(api_key="sk-test-key")
        knowledge = make_test_knowledge()

        context = engine._build_context_string(knowledge)

        assert "Test project with main and utils" in context

    @patch("app.explanation_engine.settings")
    def test_context_includes_file_summaries(self, mock_settings):
        """Context string should include file summaries."""
        mock_settings.openai_api_key = "sk-test-key"
        from app.explanation_engine import ExplanationEngine

        engine = ExplanationEngine(api_key="sk-test-key")
        knowledge = make_test_knowledge()

        context = engine._build_context_string(knowledge)

        assert "main.py" in context
        assert "utils.py" in context

    @patch("app.explanation_engine.settings")
    def test_context_includes_function_names(self, mock_settings):
        """Context string should include function names."""
        mock_settings.openai_api_key = "sk-test-key"
        from app.explanation_engine import ExplanationEngine

        engine = ExplanationEngine(api_key="sk-test-key")
        knowledge = make_test_knowledge()

        context = engine._build_context_string(knowledge)

        assert "main" in context
        assert "helper" in context


class TestExplanationSetCompleteness:
    """Test that ExplanationSet contains all required fields."""

    def test_explanation_set_has_overview(self):
        """ExplanationSet should have overview_explanation field."""
        es = ExplanationSet(
            overview_explanation="Test overview",
        )
        assert es.overview_explanation == "Test overview"

    def test_explanation_set_has_flow(self):
        """ExplanationSet should have flow_explanation field."""
        es = ExplanationSet(
            flow_explanation="Test flow",
        )
        assert es.flow_explanation == "Test flow"

    def test_explanation_set_has_per_file(self):
        """ExplanationSet should have per_file_explanations field."""
        es = ExplanationSet(
            per_file_explanations={"main.py": "Main file explanation"},
        )
        assert "main.py" in es.per_file_explanations
        assert es.per_file_explanations["main.py"] == "Main file explanation"

    def test_explanation_set_has_project_summary(self):
        """ExplanationSet should have project_summary field."""
        es = ExplanationSet(
            project_summary="Project is about testing",
        )
        assert es.project_summary == "Project is about testing"

    def test_explanation_set_defaults_to_empty(self):
        """ExplanationSet should have sensible defaults."""
        es = ExplanationSet()
        assert es.overview_explanation is None
        assert es.flow_explanation is None
        assert es.per_file_explanations == {}
        assert es.project_summary is None


class TestRetryLogic:
    """Test retry with exponential backoff logic."""

    @patch("app.explanation_engine.settings")
    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self, mock_settings):
        """A successful API call should not trigger retries."""
        mock_settings.openai_api_key = "sk-test-key"
        from app.explanation_engine import ExplanationEngine

        engine = ExplanationEngine(api_key="sk-test-key")

        call_count = 0

        async def success():
            nonlocal call_count
            call_count += 1
            return "result"

        result = await engine._retry_with_backoff(success)
        assert result == "result"
        assert call_count == 1
