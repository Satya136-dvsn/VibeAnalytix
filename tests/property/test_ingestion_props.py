"""
Property-based tests for Ingestion Service using Hypothesis.
Tests statistical properties across randomly generated inputs.
"""

import tempfile
import zipfile
from pathlib import Path
from io import BytesIO

import pytest
from hypothesis import given, settings, strategies as st

from app.ingestion import (
    validate_github_url,
    InvalidURLError,
    check_path_traversal,
)


# Strategies for generating test data
valid_github_urls = st.text(
    alphabet=st.characters(blacklist_characters="/ ")
).filter(lambda x: x and not x.startswith("."))

alphanumeric = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1)
github_url_strategy = st.builds(
    lambda owner, repo: f"https://github.com/{owner}/{repo}",
    owner=alphanumeric,
    repo=alphanumeric,
)


class TestGitHubURLValidationProperties:
    """Property-based tests for GitHub URL validation (Property 1)."""

    # Feature: vibeanalytix, Property 1: Invalid URL Rejection
    @given(github_url_strategy)
    @settings(max_examples=100)
    def test_valid_github_url_accepted(self, url):
        """For valid GitHub URLs, validation should not raise."""
        result = validate_github_url(url)
        assert result is not None
        assert "github.com" in result

    # Feature: vibeanalytix, Property 1: Invalid URL Rejection (SSH variant)
    @given(alphanumeric, alphanumeric)
    @settings(max_examples=50)
    def test_ssh_url_rejected(self, owner, repo):
        """SSH URLs should always be rejected."""
        ssh_url = f"git@github.com:{owner}/{repo}.git"
        with pytest.raises(InvalidURLError):
            validate_github_url(ssh_url)

    # Feature: vibeanalytix, Property 1: Invalid URL Rejection (HTTP variant)
    @given(alphanumeric, alphanumeric)
    @settings(max_examples=50)
    def test_http_url_rejected(self, owner, repo):
        """HTTP URLs should always be rejected."""
        http_url = f"http://github.com/{owner}/{repo}"
        with pytest.raises(InvalidURLError):
            validate_github_url(http_url)


class TestPathTraversalProperties:
    """Property-based tests for path traversal detection (Property 2)."""

    # Feature: vibeanalytix, Property 2: ZIP Path Traversal Containment
    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=1))
    @settings(max_examples=100)
    def test_normal_path_safe(self, filename):
        """Normal filenames should never trigger traversal detection."""
        path = f"folder/{filename}.txt"
        assert check_path_traversal(path) is False

    @given(st.text(min_size=1))
    @settings(max_examples=50)
    def test_double_dot_detected(self, prefix):
        """Paths with '..' should always be detected."""
        if ".." not in prefix:  # Make sure we have the traversal sequence
            path = f"{prefix}/../../../etc/passwd"
            assert check_path_traversal(path) is True


class TestZIPIntegrityProperties:
    """Property-based tests for ZIP file integrity (Property 3)."""

    # Feature: vibeanalytix, Property 3: Invalid ZIP Rejection
    @given(st.binary(min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_random_binary_rejected(self, data):
        """Random binary data should be rejected as invalid ZIP."""
        if not data.startswith(b"PK\x03\x04"):
            from app.ingestion import validate_zip_magic_bytes, InvalidZipError

            with pytest.raises(InvalidZipError):
                validate_zip_magic_bytes(data)

    def test_generated_zipfile_accepted(self):
        """Generated ZIP files should always be accepted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "test.zip"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("file1.txt", "content1")
                zf.writestr("file2.txt", "content2")

            with open(zip_path, "rb") as f:
                content = f.read()

            from app.ingestion import validate_zip_magic_bytes

            # Should not raise
            validate_zip_magic_bytes(content)
