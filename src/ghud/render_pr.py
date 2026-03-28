"""PR rendering — list and detail views."""

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _days_ago(iso_date: str) -> int:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, AttributeError):
        return 0


def _short_repo(full_name: str) -> str:
    parts = full_name.split("/")
    return parts[1] if len(parts) == 2 else full_name


def _check_status_indicator(checks: list[dict]) -> Text:
    """Return a single-character check status indicator.

    ✓ = all passing, ✗ = any failing, ● = pending, — = no checks.
    """
    if not checks:
        return Text("—", style="dim")

    has_failure = any(
        c.get("conclusion") in ("FAILURE", "CANCELLED", "TIMED_OUT")
        for c in checks
    )
    if has_failure:
        return Text("✗", style="bold red")

    has_pending = any(
        c.get("status") != "COMPLETED"
        for c in checks
    )
    if has_pending:
        return Text("●", style="yellow")

    return Text("✓", style="green")


def _review_indicator(decision: str) -> str:
    """Short review status string."""
    mapping = {
        "APPROVED": "✓",
        "CHANGES_REQUESTED": "✗",
        "REVIEW_REQUIRED": "●",
    }
    return mapping.get(decision, "")


def render_pr_list(
    prs: list[dict],
    repo: str | None = None,
    console: Optional[Console] = None,
) -> None:
    """Render a table of PRs."""
    if console is None:
        console = Console()

    if not prs:
        console.print("[dim]No open pull requests found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("#", style="dim", width=6)
    if repo is None:
        table.add_column("Repo", style="cyan", width=25)
    table.add_column("Title")
    table.add_column("Author", width=15)
    table.add_column("Status", width=8, justify="center")
    table.add_column("Age", justify="right", width=8)

    for pr in prs:
        number = str(pr.get("number", ""))
        title = pr.get("title", "")
        author = pr.get("author", {}).get("login", "")
        checks = pr.get("statusCheckRollup", []) or []
        review = pr.get("reviewDecision", "") or ""
        days = _days_ago(pr.get("createdAt", ""))

        check_ind = _check_status_indicator(checks)
        review_ind = _review_indicator(review)
        status = Text()
        status.append_text(check_ind)
        if review_ind:
            status.append(" ")
            status.append(review_ind)

        row = [number]
        if repo is None:
            pr_repo = pr.get("repository", {}).get("nameWithOwner", "")
            row.append(_short_repo(pr_repo))
        row.extend([title, author, status, f"{days}d"])
        table.add_row(*row)

    title_text = f"Pull Requests — {repo}" if repo else "Pull Requests (all repos)"
    panel = Panel(table, title=f"[bold]{title_text}[/bold]", border_style="yellow")
    console.print(panel)
