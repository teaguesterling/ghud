"""PR rendering — list and detail views."""

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
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


def render_pr_detail(
    pr: dict,
    repo: str,
    detail: str = "standard",
    max_comments: int = 3,
    console: Optional[Console] = None,
) -> None:
    """Render a detailed PR view."""
    if console is None:
        console = Console()

    number = pr.get("number", "")
    title = pr.get("title", "")
    state = pr.get("state", "OPEN")
    author = pr.get("author", {}).get("login", "unknown")
    created = pr.get("createdAt", "")
    days = _days_ago(created)
    labels = pr.get("labels", [])
    assignees = pr.get("assignees", [])
    body = pr.get("body", "")
    comments = pr.get("comments", [])
    reviews = pr.get("reviews", [])
    checks = pr.get("statusCheckRollup", []) or []
    review_decision = pr.get("reviewDecision", "") or ""
    mergeable = pr.get("mergeable", "")

    # State styling
    state_lower = state.lower()
    if state_lower == "merged":
        state_style = "magenta"
    elif state_lower == "closed":
        state_style = "red"
    else:
        state_style = "green"

    # Header
    header_lines = []
    header_lines.append(f"[bold]{title}[/bold]")

    check_ind = _check_status_indicator(checks)
    meta_parts = [
        f"[{state_style}]{state}[/{state_style}]",
        f"@{author}",
        f"{days}d ago",
        f"{len(comments)} comment{'s' if len(comments) != 1 else ''}",
    ]
    header_lines.append(" · ".join(meta_parts))

    # Review + check status line
    status_parts = []
    status_parts.append(f"Checks: {check_ind.plain}")
    if review_decision:
        status_parts.append(f"Review: {review_decision}")
    if mergeable:
        status_parts.append(f"Mergeable: {mergeable}")
    header_lines.append("  ".join(status_parts))

    if labels:
        header_lines.append(f"Labels: {', '.join(l['name'] for l in labels)}")
    if assignees:
        assignee_str = ", ".join(f"@{a['login']}" for a in assignees)
        header_lines.append(f"Assignees: {assignee_str}")

    console.print(Panel(
        "\n".join(header_lines),
        title=f"[bold]PR #{number} · {repo}[/bold]",
        border_style="yellow",
    ))

    # Expanded checks (full only)
    if detail == "full" and checks:
        check_lines = []
        for c in checks:
            name = c.get("name", "unknown")
            conclusion = c.get("conclusion", c.get("status", "unknown"))
            if conclusion == "SUCCESS":
                check_lines.append(f"  [green]✓[/green] {name}")
            elif conclusion in ("FAILURE", "CANCELLED", "TIMED_OUT"):
                check_lines.append(f"  [red]✗[/red] {name}")
            else:
                check_lines.append(f"  [yellow]●[/yellow] {name}")
        console.print(Panel(
            "\n".join(check_lines),
            title="[bold]Checks[/bold]",
            border_style="dim",
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
