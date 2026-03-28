"""Tests for repo dashboard rendering."""

from io import StringIO
from rich.console import Console
from ghud.render_repo import render_repo_dashboard


def _make_console(width=120):
    return Console(file=StringIO(), width=width, force_terminal=True)


def _get_output(console):
    console.file.seek(0)
    return console.file.read()


def test_render_repo_dashboard():
    console = _make_console()
    data = {
        "issues": [
            {"number": 1, "title": "Bug", "author": {"login": "alice"},
             "createdAt": "2026-03-20T00:00:00Z", "labels": [{"name": "bug"}]},
        ],
        "prs": [
            {"number": 10, "title": "Fix", "author": {"login": "bob"},
             "createdAt": "2026-03-21T00:00:00Z",
             "statusCheckRollup": [], "reviewDecision": ""},
        ],
    }
    render_repo_dashboard(data, repo="org/repo", console=console)
    output = _get_output(console)
    assert "Bug" in output
    assert "Fix" in output
    assert "org/repo" in output


def test_render_repo_dashboard_empty():
    console = _make_console()
    data = {"issues": [], "prs": []}
    render_repo_dashboard(data, repo="org/repo", console=console)
    output = _get_output(console)
    assert "no" in output.lower() or "org/repo" in output
