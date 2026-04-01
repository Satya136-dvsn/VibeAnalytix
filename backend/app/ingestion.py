"""
Ingestion Service for handling GitHub URLs and ZIP file uploads.

Responsibilities:
- Validate GitHub URLs (HTTPS, github.com only)
- Clone repositories with size limits
- Validate and extract ZIP files with path traversal protection
- Reject executable binaries
"""

import os
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.config import settings


@dataclass
class IngestionResult:
    """Result of ingestion operation."""

    job_id: str
    temp_dir: Path
    source_type: Literal["github", "zip"]
    repo_size_bytes: int


class IngestionError(Exception):
    """Base exception for ingestion errors."""

    pass


class InvalidURLError(IngestionError):
    """Raised when GitHub URL is invalid."""

    pass


class SizeLimitError(IngestionError):
    """Raised when file size exceeds limit."""

    pass


class InvalidZipError(IngestionError):
    """Raised when ZIP file is invalid."""

    pass


class ExecutableBinaryError(IngestionError):
    """Raised when archive contains executable files."""

    pass


class InvalidPathError(IngestionError):
    """Raised when ZIP contains path traversal sequences."""

    pass


GITHUB_URL_PATTERN = r"^https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?$"
EXECUTABLE_EXTENSIONS = {".exe", ".dll", ".so", ".bin"}
ZIP_MAGIC_BYTES = b"PK\x03\x04"


def validate_github_url(url: str) -> str:
    """
    Validate GitHub URL format.

    Args:
        url: GitHub repository URL

    Returns:
        Validated URL

    Raises:
        InvalidURLError: If URL is malformed or not from github.com
    """
    # Remove trailing .git if present
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]

    if not re.match(GITHUB_URL_PATTERN, url):
        raise InvalidURLError(
            "Only HTTPS GitHub URLs are supported. "
            "Expected format: https://github.com/owner/repo"
        )

    return url


def clone_github_repository(url: str, temp_dir: Path) -> int:
    """
    Clone a GitHub repository using git clone --depth 1.

    Args:
        url: GitHub repository URL
        temp_dir: Destination directory

    Returns:
        Size in bytes

    Raises:
        InvalidURLError: If URL is invalid
        SizeLimitError: If repository exceeds size limit
        IngestionError: If cloning fails
    """
    # Validate URL
    url = validate_github_url(url)

    try:
        # Shallow clone
        subprocess.run(
            ["git", "clone", "--depth", "1", url, str(temp_dir)],
            check=True,
            capture_output=True,
            timeout=300,  # 5 minute timeout
        )
    except subprocess.CalledProcessError as e:
        # Clean up partial clone
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise IngestionError(f"Failed to clone repository: {e.stderr.decode()}") from e
    except FileNotFoundError as e:
        raise IngestionError("Git is not installed on the system") from e
    except subprocess.TimeoutExpired as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise IngestionError("Repository cloning timed out") from e

    # Remove .git directory to save space
    git_dir = temp_dir / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    # Calculate size
    repo_size = sum(
        f.stat().st_size for f in temp_dir.rglob("*") if f.is_file()
    )

    # Enforce size limit
    max_size_bytes = settings.max_repo_size_mb * 1024 * 1024
    if repo_size > max_size_bytes:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise SizeLimitError(
            f"Repository size ({repo_size / (1024*1024):.1f} MB) "
            f"exceeds limit ({settings.max_repo_size_mb} MB)"
        )

    return repo_size


def validate_zip_magic_bytes(file_bytes: bytes) -> None:
    """
    Validate ZIP file magic bytes.

    Args:
        file_bytes: File contents

    Raises:
        InvalidZipError: If magic bytes don't match
    """
    if not file_bytes.startswith(ZIP_MAGIC_BYTES):
        raise InvalidZipError(
            "Invalid ZIP file. File does not start with ZIP magic bytes (PK\\x03\\x04)"
        )


def check_path_traversal(path: str) -> bool:
    """
    Check if a path contains traversal sequences.

    Handles both Unix-style (../) and Windows-style (..\\) sequences,
    as well as absolute paths.

    Args:
        path: Path to check

    Returns:
        True if path contains traversal sequences or is absolute
    """
    # Normalize to forward slashes for consistent checking
    normalized = path.replace("\\", "/")
    if ".." in normalized:
        return True
    if os.path.isabs(path):
        return True
    # Also check for Windows drive letters (e.g., C:/, D:\\)
    if len(path) >= 2 and path[1] == ":":
        return True
    return False


def extract_zip_file(file_bytes: bytes, temp_dir: Path) -> None:
    """
    Extract ZIP file with path traversal protection.

    Args:
        file_bytes: ZIP file contents
        temp_dir: Destination directory

    Raises:
        InvalidZipError: If ZIP is invalid
        ExecutableBinaryError: If ZIP contains executable files
        InvalidPathError: If ZIP contains path traversal sequences
        IngestionError: If extraction fails
    """
    # Validate magic bytes
    validate_zip_magic_bytes(file_bytes)

    # Check file size limit
    max_size_bytes = settings.max_zip_size_mb * 1024 * 1024
    if len(file_bytes) > max_size_bytes:
        raise SizeLimitError(
            f"ZIP file size ({len(file_bytes) / (1024*1024):.1f} MB) "
            f"exceeds limit ({settings.max_zip_size_mb} MB)"
        )

    try:
        # Open ZIP - do a single pass through entries
        with zipfile.ZipFile(__import__("io").BytesIO(file_bytes)) as zf:
            # Single pass: validate and extract simultaneously
            for info in zf.infolist():
                # Normalize filename to forward slashes
                normalized_name = info.filename.replace("\\", "/")

                # Check for path traversal
                if check_path_traversal(normalized_name):
                    raise InvalidPathError(
                        f"ZIP contains path traversal sequence: {info.filename}"
                    )

                # Check for executable binaries
                if any(normalized_name.lower().endswith(ext) for ext in EXECUTABLE_EXTENSIONS):
                    raise ExecutableBinaryError(
                        f"ZIP contains executable file: {info.filename}"
                    )

                # Sanitize path - remove leading slashes, resolve ..
                safe_path = normalized_name.lstrip("/")
                # Split and resolve any .. components
                parts = safe_path.split("/")
                resolved_parts = []
                for part in parts:
                    if part == "..":
                        if resolved_parts:
                            resolved_parts.pop()
                        # else: .. at start stays at start (safe)
                    elif part and part != ".":
                        resolved_parts.append(part)
                safe_path = "/".join(resolved_parts) if resolved_parts else "."

                target_path = (temp_dir / safe_path).resolve()

                # Verify extraction target is within temp_dir
                temp_resolved = str(temp_dir.resolve())
                target_str = str(target_path)
                if not target_str.startswith(temp_resolved + "/") and target_str != temp_resolved:
                    raise InvalidPathError(
                        f"Attempted to extract outside temp directory: {info.filename}"
                    )

                # Extract
                if info.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(info) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)

    except zipfile.BadZipFile as e:
        raise InvalidZipError("ZIP file is corrupted or invalid") from e
    except (InvalidZipError, ExecutableBinaryError, InvalidPathError):
        raise
    except Exception as e:
        raise IngestionError(f"Failed to extract ZIP file: {str(e)}") from e


async def ingest_github(job_id: str, url: str) -> IngestionResult:
    """
    Ingest a GitHub repository.

    Args:
        job_id: Unique job identifier
        url: GitHub repository URL

    Returns:
        IngestionResult with temp directory and metadata

    Raises:
        InvalidURLError: If URL is invalid
        SizeLimitError: If repository exceeds size limit
        IngestionError: If cloning fails
    """
    # Create temp directory
    temp_base = Path("/tmp") / "vibeanalytix" / job_id
    temp_base.mkdir(parents=True, exist_ok=True)

    try:
        repo_size = clone_github_repository(url, temp_base)
        return IngestionResult(
            job_id=job_id,
            temp_dir=temp_base,
            source_type="github",
            repo_size_bytes=repo_size,
        )
    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_base, ignore_errors=True)
        raise


async def ingest_zip(job_id: str, file_bytes: bytes) -> IngestionResult:
    """
    Ingest a ZIP file upload.

    Args:
        job_id: Unique job identifier
        file_bytes: ZIP file contents

    Returns:
        IngestionResult with temp directory and metadata

    Raises:
        InvalidZipError: If ZIP is invalid
        SizeLimitError: If ZIP exceeds size limit
        ExecutableBinaryError: If ZIP contains executables
        IngestionError: If extraction fails
    """
    # Create temp directory
    temp_base = Path("/tmp") / "vibeanalytix" / job_id
    temp_base.mkdir(parents=True, exist_ok=True)

    try:
        extract_zip_file(file_bytes, temp_base)

        # Calculate extracted size
        repo_size = sum(
            f.stat().st_size for f in temp_base.rglob("*") if f.is_file()
        )

        return IngestionResult(
            job_id=job_id,
            temp_dir=temp_base,
            source_type="zip",
            repo_size_bytes=repo_size,
        )
    except Exception as e:
        # Clean up on error
        shutil.rmtree(temp_base, ignore_errors=True)
        raise
