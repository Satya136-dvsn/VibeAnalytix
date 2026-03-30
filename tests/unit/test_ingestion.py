"""
Unit tests for Ingestion Service.
Tests specific GitHub URL and ZIP validation scenarios.
"""

import pytest
import tempfile
import zipfile
from pathlib import Path

from app.ingestion import (
    validate_github_url,
    InvalidURLError,
    InvalidZipError,
    ExecutableBinaryError,
    InvalidPathError,
    check_path_traversal,
    validate_zip_magic_bytes,
)


class TestGitHubURLValidation:
    """Test GitHub URL validation (Property 1)."""

    def test_valid_github_url(self):
        """Test valid GitHub URLs are accepted."""
        urls = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "https://github.com/owner-name/repo-name",
            "https://github.com/owner123/repo_name",
        ]
        for url in urls:
            result = validate_github_url(url)
            assert result is not None

    def test_invalid_github_url_ssh(self):
        """Test SSH URLs are rejected."""
        with pytest.raises(InvalidURLError):
            validate_github_url("git@github.com:owner/repo.git")

    def test_invalid_github_url_http(self):
        """Test HTTP URLs are rejected."""
        with pytest.raises(InvalidURLError):
            validate_github_url("http://github.com/owner/repo")

    def test_invalid_github_url_non_github(self):
        """Test non-GitHub URLs are rejected."""
        with pytest.raises(InvalidURLError):
            validate_github_url("https://gitlab.com/owner/repo")

    def test_invalid_github_url_malformed(self):
        """Test malformed URLs are rejected."""
        urls = [
            "https://github.com/owner",
            "https://github.com/",
            "invalid-url",
            "",
        ]
        for url in urls:
            with pytest.raises(InvalidURLError):
                validate_github_url(url)


class TestPathTraversal:
    """Test path traversal detection (Property 2)."""

    def test_path_with_double_dot(self):
        """Test detection of .. sequences."""
        assert check_path_traversal("../etc/passwd") is True
        assert check_path_traversal("subfolder/../../../etc/passwd") is True

    def test_absolute_path(self):
        """Test detection of absolute paths."""
        assert check_path_traversal("/etc/passwd") is True
        assert check_path_traversal("C:\\Windows\\System32") is True

    def test_safe_path(self):
        """Test safe paths are allowed."""
        assert check_path_traversal("file.txt") is False
        assert check_path_traversal("subfolder/file.txt") is False
        assert check_path_traversal("deep/nested/folder/file.txt") is False


class TestZIPValidation:
    """Test ZIP file validation (Property 3)."""

    def test_invalid_zip_magic_bytes(self):
        """Test non-ZIP files are rejected."""
        # Create fake file content
        fake_content = b"This is not a ZIP file"
        with pytest.raises(InvalidZipError):
            validate_zip_magic_bytes(fake_content)

    def test_valid_zip_magic_bytes(self):
        """Test valid ZIP magic bytes are accepted."""
        # Create a minimal valid ZIP
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("test.txt", "content")

            with open(zip_path, "rb") as f:
                content = f.read()
                # Should not raise
                validate_zip_magic_bytes(content)


class TestExecutableBinaryRejection:
    """Test executable binary rejection (Property 28)."""

    def test_exe_file_rejected(self):
        """Test .exe files are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("malware.exe", b"fake exe content")

            with open(zip_path, "rb") as f:
                content = f.read()

            # Should raise ExecutableBinaryError
            from app.ingestion import extract_zip_file

            with pytest.raises(ExecutableBinaryError):
                extract_zip_file(content, Path(tmpdir) / "extract")

    def test_dll_file_rejected(self):
        """Test .dll files are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("library.dll", b"fake dll")

            with open(zip_path, "rb") as f:
                content = f.read()

            from app.ingestion import extract_zip_file

            with pytest.raises(ExecutableBinaryError):
                extract_zip_file(content, Path(tmpdir) / "extract")

    def test_source_files_accepted(self):
        """Test source files are accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("main.py", "print('hello')")
                zf.writestr("README.md", "# Project")

            with open(zip_path, "rb") as f:
                content = f.read()

            from app.ingestion import extract_zip_file

            extract_dir = Path(tmpdir) / "extract"
            extract_zip_file(content, extract_dir)

            assert (extract_dir / "main.py").exists()
            assert (extract_dir / "README.md").exists()
