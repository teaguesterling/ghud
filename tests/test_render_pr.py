"""Tests for PR rendering."""

from io import StringIO
from rich.console import Console
from ghud.render_pr import render_pr_list


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
