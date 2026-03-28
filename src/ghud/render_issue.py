"""Issue rendering — list and detail views."""

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _days_ago(iso_date: str) -> int:
    """Calculate days between an ISO date string and now."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, AttributeError):
        return 0


def _short_repo(full_name: str) -> str:
    """Shorten repo name: 'owner/repo' -> 'repo'."""
    parts = full_name.split("/")
    return parts[1] if len(parts) == 2 else full_name


def render_issue_list(
    issues: list[dict],
    repo: str | None = None,
    console: Optional[Console] = None,
) -> None:
    """Render a table of issues.

    Args:
        issues: List of issue dicts.
        repo: If set, single-repo mode (no repo column). If None, cross-repo mode.
        console: Rich Console. Created if not provided.
    """
    if console is None:
        console = Console()

    if not issues:
        console.print("[dim]No open issues found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("#", style="dim", width=6)
    if repo is None:
        table.add_column("Repo", style="cyan", width=25)
    table.add_column("Title")
    table.add_column("Author", width=15)
    table.add_column("Labels", width=20)
    table.add_column("Age", justify="right", width=8)

    for issue in issues:
        number = str(issue.get("number", ""))
        title = issue.get("title", "")
        author = issue.get("author", {}).get("login", "")
        labels = ", ".join(l["name"] for l in issue.get("labels", []))
        days = _days_ago(issue.get("createdAt", ""))
        age = f"{days}d"

        row = [number]
        if repo is None:
            issue_repo = issue.get("repo", "")
            row.append(_short_repo(issue_repo))
        row.extend([title, author, labels, age])
        table.add_row(*row)

    title_text = f"Issues — {repo}" if repo else "Issues (all repos)"
    panel = Panel(table, title=f"[bold]{title_text}[/bold]", border_style="blue")
    console.print(panel)


def render_issue_detail(
    issue: dict,
    repo: str,
    detail: str = "standard",
    max_comments: int = 3,
    console: Optional[Console] = None,
) -> None:
    """Render a detailed issue view.

    Args:
        issue: Issue dict from get_issue_detail.
        repo: Repository identifier (owner/repo).
        detail: One of 'brief', 'summary', 'standard', 'full'.
        max_comments: Max comments to show (ignored for 'full' which shows all).
        console: Rich Console.
    """
    if console is None:
        console = Console()

    number = issue.get("number", "")
    title = issue.get("title", "")
    state = issue.get("state", "unknown")
    author = issue.get("author", {}).get("login", "unknown")
    created = issue.get("createdAt", "")
    days = _days_ago(created)
    labels = issue.get("labels", [])
    assignees = issue.get("assignees", [])
    milestone = issue.get("milestone")
    body = issue.get("body", "")
    comments = issue.get("comments", [])

    # Header
    state_style = "green" if state.lower() == "open" else "red"
    header_lines = []
    header_lines.append(f"[bold]{title}[/bold]")
    meta_parts = [
        f"[{state_style}]{state}[/{state_style}]",
        f"@{author}",
        f"{days}d ago",
        f"{len(comments)} comment{'s' if len(comments) != 1 else ''}",
    ]
    header_lines.append(" · ".join(meta_parts))

    if labels:
        label_str = ", ".join(l["name"] for l in labels)
        header_lines.append(f"Labels: {label_str}")
    if milestone:
        header_lines.append(f"Milestone: {milestone.get('title', '')}")
    if assignees:
        assignee_str = ", ".join(f"@{a['login']}" for a in assignees)
        header_lines.append(f"Assignees: {assignee_str}")

    header_text = "\n".join(header_lines)
    console.print(Panel(
        header_text,
        title=f"[bold]Issue #{number} · {repo}[/bold]",
        border_style="blue",
    ))

    # Body (standard and full only)
    if detail in ("standard", "full") and body:
        console.print(Panel(
            Markdown(body),
            title="[bold]Description[/bold]",
            border_style="dim",
        ))

    # Comments
    if detail == "brief":
        # Brief: just the count, already in header
        return

    if detail in ("full", "summary"):
        display_comments = comments
    else:
        display_comments = comments[-max_comments:] if max_comments else comments

    if not comments:
        return

    total = len(comments)
    showing = len(display_comments)
    if showing < total:
        comment_title = f"Comments (showing {showing} of {total})"
    else:
        comment_title = f"Comments ({total})"

    comment_parts = []
    for c in display_comments:
        c_author = c.get("author", {}).get("login", "unknown")
        c_date = c.get("createdAt", "")
        c_days = _days_ago(c_date)
        c_body = c.get("body", "")

        if detail == "summary":
            comment_parts.append(f"[bold]@{c_author}[/bold] · {c_days}d ago")
        else:
            comment_parts.append(f"[bold]@{c_author}[/bold] · {c_days}d ago\n{c_body}")

    console.print(Panel(
        "\n\n".join(comment_parts),
        title=f"[bold]{comment_title}[/bold]",
        border_style="dim",
    ))
