"""Tests for issue rendering."""

from io import StringIO
from rich.console import Console
from ghud.render_issue import render_issue_list


def _make_console(width=120):
    return Console(file=StringIO(), width=width, force_terminal=True)


def _get_output(console):
    console.file.seek(0)
    return console.file.read()


def test_render_issue_list_single_repo():
    console = _make_console()
    issues = [
        {"number": 1, "title": "Bug report", "author": {"login": "alice"},
         "createdAt": "2026-03-20T00:00:00Z", "labels": [{"name": "bug"}]},
        {"number": 2, "title": "Feature request", "author": {"login": "bob"},
         "createdAt": "2026-03-19T00:00:00Z", "labels": []},
    ]
    render_issue_list(issues, repo="org/repo", console=console)
    output = _get_output(console)
    assert "Bug report" in output
    assert "Feature request" in output
    assert "alice" in output
    assert "bug" in output


def test_render_issue_list_cross_repo():
    console = _make_console()
    issues = [
        {"number": 1, "title": "Bug", "author": {"login": "alice"},
         "createdAt": "2026-03-20T00:00:00Z", "labels": [],
         "repo": "org/repo-a"},
        {"number": 5, "title": "Feature", "author": {"login": "bob"},
         "createdAt": "2026-03-19T00:00:00Z", "labels": [],
         "repo": "org/repo-b"},
    ]
    render_issue_list(issues, repo=None, console=console)
    output = _get_output(console)
    assert "Bug" in output
    assert "repo-a" in output
    assert "repo-b" in output


def test_render_issue_list_empty():
    console = _make_console()
    render_issue_list([], repo="org/repo", console=console)
    output = _get_output(console)
    assert "no" in output.lower() or "no open issues" in output.lower()
