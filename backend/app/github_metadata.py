"""
GitHub Metadata Enrichment — no API key required for public repos.

Uses GitHub REST API (https://api.github.com), which allows 60 req/hr
unauthenticated and 5000 req/hr with a token. Gracefully skips on any failure.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_GITHUB_API_BASE = "https://api.github.com"
_TIMEOUT = 8.0  # seconds


@dataclass
class RepoMetadata:
    """Metadata fetched from the GitHub REST API."""
    name: str = ""
    full_name: str = ""
    description: str = ""
    stars: int = 0
    forks: int = 0
    language: str = ""
    topics: list[str] = field(default_factory=list)
    license_name: str = ""
    default_branch: str = "main"
    is_private: bool = False
    open_issues: int = 0
    homepage: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "stars": self.stars,
            "forks": self.forks,
            "language": self.language,
            "topics": self.topics,
            "license_name": self.license_name,
            "default_branch": self.default_branch,
            "open_issues": self.open_issues,
            "homepage": self.homepage,
        }


def _parse_owner_repo(github_url: str) -> Optional[tuple[str, str]]:
    """Extract (owner, repo) from a GitHub URL."""
    pattern = r"github\.com/([^/]+)/([^/\.\s]+?)(?:\.git)?$"
    m = re.search(pattern, github_url.strip())
    if m:
        return m.group(1), m.group(2)
    return None


async def fetch_repo_metadata(github_url: str) -> Optional[RepoMetadata]:
    """
    Fetch repository metadata from the GitHub REST API.

    Args:
        github_url: Full GitHub repo URL (e.g. https://github.com/owner/repo)

    Returns:
        RepoMetadata instance, or None on any error/failure
    """
    parsed = _parse_owner_repo(github_url)
    if not parsed:
        logger.debug("Could not parse GitHub URL: %s", github_url)
        return None

    owner, repo = parsed
    api_url = f"{_GITHUB_API_BASE}/repos/{owner}/{repo}"

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "VibeAnalytix/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(api_url, headers=headers)
            if resp.status_code == 404:
                logger.debug("GitHub repo not found (private or non-existent): %s", api_url)
                return None
            if resp.status_code != 200:
                logger.debug("GitHub API returned %d for %s", resp.status_code, api_url)
                return None

            data = resp.json()

        meta = RepoMetadata(
            name=data.get("name", repo),
            full_name=data.get("full_name", f"{owner}/{repo}"),
            description=data.get("description") or "",
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            language=data.get("language") or "",
            topics=data.get("topics", []),
            license_name=(data.get("license") or {}).get("name", ""),
            default_branch=data.get("default_branch", "main"),
            is_private=data.get("private", False),
            open_issues=data.get("open_issues_count", 0),
            homepage=data.get("homepage") or "",
        )
        logger.info("Fetched GitHub metadata for %s/%s (%d ⭐)", owner, repo, meta.stars)
        return meta

    except Exception as exc:
        # Network errors, timeouts, JSON decode failures — all non-fatal
        logger.debug("GitHub metadata fetch failed for %s: %s", github_url, exc)
        return None
