from io import StringIO
from rich.console import Console
from ghud.dashboard import render_dashboard


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
