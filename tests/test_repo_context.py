import subprocess
import pytest
from ghud.repo_context import resolve_repo


def _mock_run(stdout_data, returncode=0):
    def mock(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, returncode)
        result.stdout = stdout_data
        result.stderr = ""
        return result
    return mock


def test_resolve_repo_from_explicit_flag():
    """--repo flag takes priority over git detection."""
    assert resolve_repo(repo_flag="owner/myrepo") == "owner/myrepo"


def test_resolve_repo_from_explicit_flag_all():
    """--repo all returns None (meaning cross-repo)."""
    assert resolve_repo(repo_flag="all") is None


def test_resolve_repo_from_git_remote_https(monkeypatch):
    """Detects repo from HTTPS git remote."""
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("https://github.com/owner/myrepo.git\n"),
    )
    assert resolve_repo() == "owner/myrepo"


def test_resolve_repo_from_git_remote_ssh(monkeypatch):
    """Detects repo from SSH git remote."""
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("git@github.com:owner/myrepo.git\n"),
    )
    assert resolve_repo() == "owner/myrepo"


def test_resolve_repo_no_git_returns_none(monkeypatch):
    """Returns None when not in a git repo."""
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("", returncode=1),
    )
    assert resolve_repo() is None
