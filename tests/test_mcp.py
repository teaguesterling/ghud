# tests/test_mcp.py
import json
import subprocess
import pytest
from unittest.mock import patch


def _mock_run(stdout_data, returncode=0):
    def mock(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, returncode)
        result.stdout = stdout_data if isinstance(stdout_data, str) else json.dumps(stdout_data)
        result.stderr = ""
        return result
    return mock


@pytest.fixture
def mock_config():
    """Patch lazy state so no real GitHub calls are made."""
    import ghud.mcp as mcp_mod
    mcp_mod._state = {"repos": ["testuser/tool_a"], "username": "testuser"}
    yield
    mcp_mod._state = None  # reset for other tests


def test_get_portfolio_repos(mock_config):
    from ghud.mcp import get_portfolio_repos
    result = get_portfolio_repos()
    assert "testuser/tool_a" in result


def test_get_notifications_tool(mock_config, monkeypatch):
    obj = {"reason": "review_requested", "subject": {"title": "Fix"}, "repository": {"full_name": "testuser/tool_a"}}
    monkeypatch.setattr(subprocess, "run", _mock_run(json.dumps(obj)))
    from ghud.mcp import get_notifications_tool
    result = get_notifications_tool(important_only=True)
    assert len(result) == 1


def test_get_open_prs_tool(mock_config, monkeypatch):
    data = [{"title": "PR", "repository": {"nameWithOwner": "testuser/tool_a"},
             "state": "open", "createdAt": "2026-03-20T00:00:00Z", "updatedAt": "2026-03-22T00:00:00Z",
             "url": "https://...", "commentsCount": 0}]
    monkeypatch.setattr(subprocess, "run", _mock_run(data))
    from ghud.mcp import get_open_prs_tool
    result = get_open_prs_tool()
    assert len(result) == 1


def test_get_dashboard_returns_markdown(mock_config, monkeypatch):
    # Mock all GitHub calls to return empty
    monkeypatch.setattr(subprocess, "run", _mock_run("", returncode=1))
    from ghud.mcp import get_dashboard
    result = get_dashboard(show_all=False, days=7)
    assert isinstance(result, str)
