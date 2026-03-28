"""Git remote detection and --repo flag resolution."""

import re
import subprocess


def _get_git_remote_url() -> str:
    """Get the origin remote URL from the current git directory."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _parse_repo_from_url(url: str) -> str | None:
    """Extract owner/repo from a GitHub remote URL."""
    # HTTPS: https://github.com/owner/repo.git
    # SSH: git@github.com:owner/repo.git
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if match:
        return match.group(1)
    return None


def resolve_repo(repo_flag: str | None = None) -> str | None:
    """Resolve the target repo.

    Returns owner/repo string, or None for cross-repo mode.
    - If repo_flag is provided and not "all", use it directly.
    - If repo_flag is "all", return None (cross-repo).
    - Otherwise, detect from git remote. Returns None if not in a git repo.
    """
    if repo_flag is not None:
        if repo_flag == "all":
            return None
        return repo_flag

    url = _get_git_remote_url()
    if not url:
        return None
    return _parse_repo_from_url(url)
