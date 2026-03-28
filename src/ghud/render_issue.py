"""Issue rendering — list and detail views."""

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
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
