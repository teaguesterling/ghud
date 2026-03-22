from io import StringIO
from rich.console import Console
from ghud.dashboard import render_dashboard, render_dashboard_markdown


def _make_console(width=140):
    """Create a console that captures output."""
    return Console(file=StringIO(), width=width, force_terminal=True)


def _get_output(console):
    console.file.seek(0)
    return console.file.read()


def test_render_with_notifications():
    console = _make_console()
    data = {
        "notifications": [
            {"reason": "review_requested",
             "subject": {"title": "Fix bug", "type": "PullRequest"},
             "repository": {"full_name": "org/repo"}},
        ],
        "open_prs": [],
        "merged_prs": [],
        "other_issues": [],
        "other_activity": [],
    }
    render_dashboard(data, console=console, show_all=False)
    output = _get_output(console)
    assert "Fix bug" in output
    assert "review_requested" in output


def test_render_hides_empty_sections():
    console = _make_console()
    data = {
        "notifications": [],
        "open_prs": [],
        "merged_prs": [],
        "other_issues": [],
        "other_activity": [],
    }
    render_dashboard(data, console=console, show_all=False)
    output = _get_output(console)
    assert "Notifications" not in output
    assert "No activity to show." in output


def test_render_narrow_is_single_column():
    console = _make_console(width=80)
    data = {
        "notifications": [
            {"reason": "mention",
             "subject": {"title": "Question", "type": "Issue"},
             "repository": {"full_name": "org/repo"}},
        ],
        "open_prs": [
            {"title": "My PR", "repository": {"nameWithOwner": "org/repo"},
             "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
             "commentsCount": 0},
        ],
        "merged_prs": [],
        "other_issues": [],
        "other_activity": [],
    }
    render_dashboard(data, console=console, show_all=False)
    output = _get_output(console)
    assert "Question" in output
    assert "My PR" in output


def test_render_with_all_flag_includes_subscribed():
    console = _make_console()
    data = {
        "notifications": [
            {"reason": "subscribed",
             "subject": {"title": "Noise", "type": "Issue"},
             "repository": {"full_name": "org/repo"}},
        ],
        "open_prs": [],
        "merged_prs": [],
        "other_issues": [],
        "other_activity": [],
    }
    # With show_all=False, subscribed should be filtered
    render_dashboard(data, console=console, show_all=False)
    output = _get_output(console)
    assert "Noise" not in output

    # With show_all=True, subscribed should appear
    console2 = _make_console()
    render_dashboard(data, console=console2, show_all=True)
    output2 = _get_output(console2)
    assert "Noise" in output2


def test_markdown_render_with_notifications():
    data = {
        "notifications": [
            {"reason": "review_requested",
             "subject": {"title": "Fix bug", "type": "PullRequest"},
             "repository": {"full_name": "org/repo"}},
        ],
        "open_prs": [],
        "merged_prs": [],
        "other_issues": [],
        "other_activity": [],
    }
    md = render_dashboard_markdown(data, show_all=False)
    assert "## Notifications" in md
    assert "Fix bug" in md
    assert "review_requested" in md


def test_markdown_render_hides_empty_sections():
    data = {
        "notifications": [],
        "open_prs": [],
        "merged_prs": [],
        "other_issues": [],
        "other_activity": [],
    }
    md = render_dashboard_markdown(data, show_all=False)
    assert md.strip() == "No activity to show."


def test_markdown_render_filters_subscribed():
    data = {
        "notifications": [
            {"reason": "subscribed",
             "subject": {"title": "Noise", "type": "Issue"},
             "repository": {"full_name": "org/repo"}},
        ],
        "open_prs": [],
        "merged_prs": [],
        "other_issues": [],
        "other_activity": [],
    }
    md = render_dashboard_markdown(data, show_all=False)
    assert "Noise" not in md

    md_all = render_dashboard_markdown(data, show_all=True)
    assert "Noise" in md_all


def test_markdown_render_all_sections():
    data = {
        "notifications": [
            {"reason": "mention", "subject": {"title": "Q"}, "repository": {"full_name": "org/repo"}},
        ],
        "open_prs": [
            {"title": "My PR", "repository": {"nameWithOwner": "org/repo"},
             "createdAt": "2026-03-20T00:00:00Z", "commentsCount": 2},
        ],
        "merged_prs": [
            {"title": "Done", "repository": {"nameWithOwner": "org/repo"},
             "closedAt": "2026-03-22T00:00:00Z"},
        ],
        "other_issues": [
            {"title": "Bug", "repo": "org/repo", "createdAt": "2026-03-21T00:00:00Z"},
        ],
        "other_activity": [
            {"repo": "ext/repo", "count": 3, "reasons": "subscribed"},
        ],
    }
    md = render_dashboard_markdown(data, show_all=False)
    assert "## Notifications" in md
    assert "## Your Open PRs" in md
    assert "## Recently Merged" in md
    assert "## New Issues From Others" in md
    assert "## Other Activity" in md
