"""Terminal dashboard rendering with rich."""

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ghud.data import IMPORTANT_REASONS

REASON_COLORS = {
    "review_requested": "bold red",
    "security_alert": "bold red",
    "mention": "yellow",
    "assign": "yellow",
    "team_mention": "yellow",
    "subscribed": "dim",
    "comment": "dim",
    "author": "dim",
    "ci_activity": "dim",
}


def _days_ago(iso_date: str) -> int:
    """Calculate days between an ISO date string and now."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, AttributeError):
        return 0


def _short_repo(full_name: str) -> str:
    """Shorten repo name: 'owner/repo' -> 'repo' for known owner, keep full otherwise."""
    parts = full_name.split("/")
    if len(parts) == 2:
        return parts[1]
    return full_name


def _build_notifications_panel(notifications: list[dict], show_all: bool) -> Optional[Panel]:
    """Build the notifications panel."""
    if not show_all:
        notifications = [n for n in notifications if n.get("reason") in IMPORTANT_REASONS]

    if not notifications:
        return None

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("reason", style="bold", width=18)
    table.add_column("repo", width=25)
    table.add_column("title")

    for n in notifications:
        reason = n.get("reason", "unknown")
        repo = n.get("repository", {}).get("full_name", "")
        title = n.get("subject", {}).get("title", "")
        style = REASON_COLORS.get(reason, "")
        table.add_row(
            Text(reason, style=style),
            Text(_short_repo(repo), style="cyan"),
            title,
        )

    count = len(notifications)
    label = "important" if not show_all else "all"
    return Panel(table, title=f"[bold]Notifications ({count} {label})[/bold]", border_style="red")


def _build_open_prs_panel(prs: list[dict]) -> Optional[Panel]:
    """Build the open PRs panel."""
    if not prs:
        return None

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("repo", width=25)
    table.add_column("title")
    table.add_column("age", justify="right", width=12)

    for pr in prs:
        repo = pr.get("repository", {}).get("nameWithOwner", "")
        title = pr.get("title", "")
        days = _days_ago(pr.get("createdAt", ""))
        comments = pr.get("commentsCount", 0)
        age_str = f"{days}d"
        if comments:
            age_str += f" {comments} comments"
        table.add_row(
            Text(_short_repo(repo), style="cyan"),
            title,
            Text(age_str, style="yellow"),
        )

    return Panel(table, title=f"[bold]Your Open PRs ({len(prs)})[/bold]", border_style="yellow")


def _build_merged_prs_panel(prs: list[dict]) -> Optional[Panel]:
    """Build the recently merged PRs panel."""
    if not prs:
        return None

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("repo", width=25)
    table.add_column("title")
    table.add_column("when", justify="right", width=12)

    for pr in prs:
        repo = pr.get("repository", {}).get("nameWithOwner", "")
        title = pr.get("title", "")
        days = _days_ago(pr.get("closedAt", ""))
        when_str = "today" if days == 0 else f"{days}d ago"
        table.add_row(
            Text(_short_repo(repo), style="cyan"),
            title,
            Text(when_str, style="green"),
        )

    return Panel(table, title=f"[bold]Recently Merged ({len(prs)})[/bold]", border_style="green")


def _build_issues_panel(issues: list[dict]) -> Optional[Panel]:
    """Build the new issues from others panel."""
    if not issues:
        return None

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("repo", width=25)
    table.add_column("title")
    table.add_column("age", justify="right", width=12)

    for issue in issues:
        repo = issue.get("repo", "")
        title = issue.get("title", "")
        days = _days_ago(issue.get("createdAt", ""))
        age_str = f"{days}d ago"
        table.add_row(
            Text(_short_repo(repo), style="cyan"),
            title,
            Text(age_str, style="blue"),
        )

    return Panel(table, title=f"[bold]New Issues From Others ({len(issues)})[/bold]", border_style="blue")


def _build_other_activity_panel(activity: list[dict]) -> Optional[Panel]:
    """Build the other activity panel (repos not in projects.yaml)."""
    if not activity:
        return None

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("repo", width=30)
    table.add_column("summary")

    for item in activity:
        repo = item.get("repo", "")
        count = item.get("count", 0)
        reasons = item.get("reasons", "")
        table.add_row(
            Text(repo, style="dim cyan"),
            Text(f"{count} notification{'s' if count != 1 else ''} ({reasons})", style="dim"),
        )

    return Panel(table, title="[bold dim]Other Activity[/bold dim]", border_style="dim")


def render_dashboard(
    data: dict,
    console: Optional[Console] = None,
    show_all: bool = False,
) -> None:
    """Render the full dashboard."""
    if console is None:
        console = Console()

    notifications_panel = _build_notifications_panel(data.get("notifications", []), show_all)
    open_prs_panel = _build_open_prs_panel(data.get("open_prs", []))
    merged_prs_panel = _build_merged_prs_panel(data.get("merged_prs", []))
    issues_panel = _build_issues_panel(data.get("other_issues", []))
    other_panel = _build_other_activity_panel(data.get("other_activity", []))

    # Collect non-None panels
    left_panels = [p for p in [notifications_panel, issues_panel] if p]
    right_panels = [p for p in [open_prs_panel, merged_prs_panel] if p]
    all_panels = left_panels + right_panels

    if not all_panels and not other_panel:
        console.print("[dim]No activity to show.[/dim]")
        return

    wide = console.size.width >= 120

    if wide and left_panels and right_panels:
        # Two-column layout using a grid
        grid = Table.grid(padding=(0, 2))
        grid.add_column(ratio=1)
        grid.add_column(ratio=1)

        # Pair up panels row by row
        max_rows = max(len(left_panels), len(right_panels))
        for i in range(max_rows):
            left = left_panels[i] if i < len(left_panels) else ""
            right = right_panels[i] if i < len(right_panels) else ""
            grid.add_row(left, right)

        console.print(grid)
    else:
        # Single column
        for panel in left_panels + right_panels:
            console.print(panel)

    if other_panel:
        console.print(other_panel)
