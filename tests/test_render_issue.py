"""Tests for issue rendering."""

from io import StringIO
from rich.console import Console
from ghud.render_issue import render_issue_list, render_issue_detail


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


def test_render_issue_detail_standard():
    """Standard detail: header + body + last N comments."""
    console = _make_console()
    issue = {
        "number": 42,
        "title": "Fix the thing",
        "state": "open",
        "body": "## Description\nThis needs fixing.",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "url": "https://github.com/org/repo/issues/42",
        "labels": [{"name": "bug"}, {"name": "priority-high"}],
        "assignees": [{"login": "bob"}],
        "milestone": {"title": "v2.0"},
        "comments": [
            {"author": {"login": "carol"}, "body": "I can reproduce.",
             "createdAt": "2026-03-21T00:00:00Z"},
            {"author": {"login": "dave"}, "body": "Looking into it.",
             "createdAt": "2026-03-22T00:00:00Z"},
            {"author": {"login": "eve"}, "body": "Fixed in #43.",
             "createdAt": "2026-03-23T00:00:00Z"},
        ],
    }
    render_issue_detail(issue, repo="org/repo", detail="standard", max_comments=3, console=console)
    output = _get_output(console)
    assert "Fix the thing" in output
    assert "alice" in output
    assert "bug" in output
    assert "v2.0" in output
    assert "Description" in output
    assert "Fixed in #43" in output


def test_render_issue_detail_brief():
    """Brief detail: header only, no body, comment count only."""
    console = _make_console()
    issue = {
        "number": 42,
        "title": "Fix the thing",
        "state": "open",
        "body": "Long body text that should not appear",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "milestone": None,
        "comments": [
            {"author": {"login": "carol"}, "body": "Comment 1",
             "createdAt": "2026-03-21T00:00:00Z"},
        ],
    }
    render_issue_detail(issue, repo="org/repo", detail="brief", max_comments=3, console=console)
    output = _get_output(console)
    assert "Fix the thing" in output
    assert "Long body text" not in output
    assert "Comment 1" not in output


def test_render_issue_detail_summary():
    """Summary detail: header, comment headers (no body text in comments)."""
    console = _make_console()
    issue = {
        "number": 42,
        "title": "Fix the thing",
        "state": "open",
        "body": "Body should not appear",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "milestone": None,
        "comments": [
            {"author": {"login": "carol"}, "body": "Detailed comment body",
             "createdAt": "2026-03-21T00:00:00Z"},
        ],
    }
    render_issue_detail(issue, repo="org/repo", detail="summary", max_comments=3, console=console)
    output = _get_output(console)
    assert "Fix the thing" in output
    assert "Body should not appear" not in output
    assert "carol" in output
    assert "Detailed comment body" not in output


def test_render_issue_detail_truncates_comments():
    """Only shows the last max_comments comments."""
    console = _make_console()
    issue = {
        "number": 42,
        "title": "Test",
        "state": "open",
        "body": "Body",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "milestone": None,
        "comments": [
            {"author": {"login": f"user{i}"}, "body": f"Comment {i}",
             "createdAt": f"2026-03-{20+i}T00:00:00Z"}
            for i in range(10)
        ],
    }
    render_issue_detail(issue, repo="org/repo", detail="standard", max_comments=2, console=console)
    output = _get_output(console)
    assert "Comment 8" in output
    assert "Comment 9" in output
    assert "Comment 0" not in output
    assert "showing 2 of 10" in output.lower()
