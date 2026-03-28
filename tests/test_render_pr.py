"""Tests for PR rendering."""

from io import StringIO
from rich.console import Console
from ghud.render_pr import render_pr_list, render_pr_detail


def _make_console(width=120):
    return Console(file=StringIO(), width=width, force_terminal=True)


def _get_output(console):
    console.file.seek(0)
    return console.file.read()


def test_render_pr_list_single_repo():
    console = _make_console()
    prs = [
        {"number": 10, "title": "Add feature", "author": {"login": "alice"},
         "createdAt": "2026-03-20T00:00:00Z",
         "statusCheckRollup": [
             {"status": "COMPLETED", "conclusion": "SUCCESS"},
         ],
         "reviewDecision": "APPROVED"},
        {"number": 11, "title": "Fix bug", "author": {"login": "bob"},
         "createdAt": "2026-03-21T00:00:00Z",
         "statusCheckRollup": [
             {"status": "COMPLETED", "conclusion": "FAILURE"},
         ],
         "reviewDecision": ""},
    ]
    render_pr_list(prs, repo="org/repo", console=console)
    output = _get_output(console)
    assert "Add feature" in output
    assert "Fix bug" in output
    assert "alice" in output


def test_render_pr_list_empty():
    console = _make_console()
    render_pr_list([], repo="org/repo", console=console)
    output = _get_output(console)
    assert "no" in output.lower()


def test_render_pr_list_check_status_indicators():
    """Check status should show visual indicators."""
    console = _make_console()
    prs = [
        {"number": 1, "title": "All passing", "author": {"login": "a"},
         "createdAt": "2026-03-20T00:00:00Z",
         "statusCheckRollup": [
             {"status": "COMPLETED", "conclusion": "SUCCESS"},
         ],
         "reviewDecision": "APPROVED"},
    ]
    render_pr_list(prs, repo="org/repo", console=console)
    output = _get_output(console)
    assert "✓" in output or "APPROVED" in output or "passing" in output.lower()


def test_render_pr_detail_standard():
    """Standard: header with check indicator + body + last N comments."""
    console = _make_console()
    pr = {
        "number": 15,
        "title": "Add feature X",
        "state": "OPEN",
        "body": "## Changes\nAdds feature X.",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [{"name": "enhancement"}],
        "assignees": [{"login": "bob"}],
        "reviewDecision": "APPROVED",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"name": "ci/build", "status": "COMPLETED", "conclusion": "SUCCESS"},
        ],
        "comments": [
            {"author": {"login": "carol"}, "body": "LGTM!",
             "createdAt": "2026-03-21T00:00:00Z"},
        ],
        "reviews": [
            {"author": {"login": "carol"}, "state": "APPROVED",
             "body": "", "submittedAt": "2026-03-21T00:00:00Z"},
        ],
    }
    render_pr_detail(pr, repo="org/repo", detail="standard", max_comments=3, console=console)
    output = _get_output(console)
    assert "Add feature X" in output
    assert "alice" in output
    assert "Changes" in output
    assert "LGTM" in output
    assert "✓" in output


def test_render_pr_detail_full_expands_checks():
    """Full detail: shows individual check names."""
    console = _make_console()
    pr = {
        "number": 15,
        "title": "Add feature X",
        "state": "OPEN",
        "body": "Body text",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "reviewDecision": "",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"name": "ci/build", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "ci/lint", "status": "COMPLETED", "conclusion": "FAILURE"},
        ],
        "comments": [],
        "reviews": [],
    }
    render_pr_detail(pr, repo="org/repo", detail="full", max_comments=3, console=console)
    output = _get_output(console)
    assert "ci/build" in output
    assert "ci/lint" in output


def test_render_pr_detail_brief():
    """Brief: header only, no body or comments."""
    console = _make_console()
    pr = {
        "number": 15,
        "title": "Add feature X",
        "state": "OPEN",
        "body": "Should not appear",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "reviewDecision": "",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [],
        "comments": [
            {"author": {"login": "carol"}, "body": "Hidden comment",
             "createdAt": "2026-03-21T00:00:00Z"},
        ],
        "reviews": [],
    }
    render_pr_detail(pr, repo="org/repo", detail="brief", max_comments=3, console=console)
    output = _get_output(console)
    assert "Add feature X" in output
    assert "Should not appear" not in output
    assert "Hidden comment" not in output
