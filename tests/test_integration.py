"""Integration smoke tests for CLI subcommands."""

import subprocess
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from ghud.cli import app

runner = CliRunner()


def _mock_subprocess_run(cmd, **kwargs):
    """Return plausible mock data based on the command."""
    import json
    result = subprocess.CompletedProcess(cmd, 0)
    result.stderr = ""

    # Use positional args to identify the subcommand precisely, avoiding
    # false matches from --json field names (e.g. "view" inside "reviewDecision").
    args = list(cmd) if isinstance(cmd, list) else cmd.split()
    # Strip leading program name (e.g. "gh") to get the subcommand tokens
    subargs = args[1:] if args else []

    if subargs[:2] == ["issue", "view"]:
        result.stdout = json.dumps({
            "number": 42, "title": "Test issue", "state": "open",
            "body": "Test body", "author": {"login": "tester"},
            "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
            "labels": [], "assignees": [], "milestone": None,
            "comments": [],
        })
    elif subargs[:2] == ["issue", "list"]:
        result.stdout = json.dumps([
            {"number": 1, "title": "Issue A", "author": {"login": "a"},
             "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
             "labels": []},
        ])
    elif subargs[:2] == ["pr", "view"]:
        result.stdout = json.dumps({
            "number": 15, "title": "Test PR", "state": "OPEN",
            "body": "PR body", "author": {"login": "tester"},
            "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
            "labels": [], "assignees": [], "reviewDecision": "",
            "mergeable": "MERGEABLE", "statusCheckRollup": [],
            "comments": [], "reviews": [],
        })
    elif subargs[:2] == ["pr", "list"]:
        result.stdout = json.dumps([
            {"number": 10, "title": "PR A", "author": {"login": "a"},
             "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
             "state": "OPEN", "statusCheckRollup": [], "reviewDecision": ""},
        ])
    elif "remote" in subargs:
        result.stdout = "https://github.com/org/repo.git\n"
    else:
        result.stdout = "[]"

    return result


def test_issue_list_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["issue", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
        assert "Issue A" in result.output


def test_issue_detail_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["issue", "42", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
        assert "Test issue" in result.output


def test_pr_list_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["pr", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
        assert "PR A" in result.output


def test_pr_detail_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["pr", "15", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
        assert "Test PR" in result.output


def test_repo_dashboard_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["repo", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
