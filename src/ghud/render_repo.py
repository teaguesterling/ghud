"""Repo-level dashboard rendering."""

from typing import Optional

from rich.console import Console

from ghud.render_issue import render_issue_list
from ghud.render_pr import render_pr_list


def render_repo_dashboard(
    data: dict,
    repo: str,
    console: Optional[Console] = None,
) -> None:
    """Render a repo-level dashboard with issues and PRs summary."""
    if console is None:
        console = Console()

    issues = data.get("issues", [])
    prs = data.get("prs", [])

    console.print(f"\n[bold]Repository Dashboard — {repo}[/bold]\n")

    if not issues and not prs:
        console.print("[dim]No open issues or pull requests.[/dim]")
        return

    if issues:
        render_issue_list(issues, repo=repo, console=console)
        console.print()

    if prs:
        render_pr_list(prs, repo=repo, console=console)
