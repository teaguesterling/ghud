"""CLI entry point using Typer."""

import sys
from enum import Enum
from typing import Optional

import typer

from ghud.repo_context import resolve_repo

app = typer.Typer(
    name="ghud",
    help="GitHub Heads-Up Display — terminal dashboard for your portfolio repos",
    invoke_without_command=True,
)


class DetailLevel(str, Enum):
    brief = "brief"
    summary = "summary"
    standard = "standard"
    full = "full"


class IssueState(str, Enum):
    open = "open"
    closed = "closed"
    all = "all"


def run_dashboard(show_all: bool = False, days: int = 7) -> None:
    """Run the overview dashboard (existing behavior)."""
    from ghud.config import find_yaml_path, load_repos_from_yaml
    from ghud.github import get_username
    from ghud.data import fetch_dashboard_data
    from ghud.dashboard import render_dashboard

    yaml_path = find_yaml_path()
    if not yaml_path:
        typer.echo("Error: Could not find projects.yaml", err=True)
        raise typer.Exit(1)

    repos = load_repos_from_yaml(yaml_path)
    username = get_username()

    if not username:
        typer.echo("Error: Could not determine GitHub username. Run 'gh auth login'.", err=True)
        raise typer.Exit(1)

    data = fetch_dashboard_data(repos, username, days=days)
    render_dashboard(data, show_all=show_all)


def run_discover_cmd(dry_run: bool = False) -> None:
    """Run the discover command."""
    import argparse
    from ghud.discover import run_discover

    args = argparse.Namespace(dry_run=dry_run)
    run_discover(args)


def run_serve() -> None:
    """Run the MCP server."""
    from ghud.mcp import main as mcp_main
    mcp_main()


def run_issue_list(
    repo: str | None = None,
    state: str = "open",
    limit: int = 30,
    no_pager: bool = False,
) -> None:
    """Placeholder for issue list — implemented in Task 7."""
    typer.echo("Issue list: not implemented yet")


def run_issue_detail(
    repo: str,
    number: int,
    detail: str = "standard",
    comments: str = "3",
    no_pager: bool = False,
) -> None:
    """Placeholder for issue detail — implemented in Task 8."""
    typer.echo(f"Issue detail #{number}: not implemented yet")


def run_pr_list(
    repo: str | None = None,
    state: str = "open",
    limit: int = 30,
    no_pager: bool = False,
) -> None:
    """Placeholder for PR list — implemented in Task 9."""
    typer.echo("PR list: not implemented yet")


def run_pr_detail(
    repo: str,
    number: int,
    detail: str = "standard",
    comments: str = "3",
    no_pager: bool = False,
) -> None:
    """Placeholder for PR detail — implemented in Task 10."""
    typer.echo(f"PR detail #{number}: not implemented yet")


def run_repo_dashboard(
    repo: str | None = None,
    no_pager: bool = False,
) -> None:
    """Placeholder for repo dashboard — implemented in Task 11."""
    typer.echo("Repo dashboard: not implemented yet")


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Include all notifications"),
    days: int = typer.Option(7, "--days", help="Lookback days for merged PRs"),
):
    """GitHub Heads-Up Display."""
    if ctx.invoked_subcommand is None:
        run_dashboard(show_all=show_all, days=days)


@app.command()
def overview(
    show_all: bool = typer.Option(False, "--all", help="Include all notifications"),
    days: int = typer.Option(7, "--days", help="Lookback days for merged PRs"),
):
    """Global dashboard — notifications, PRs, issues across portfolio repos."""
    run_dashboard(show_all=show_all, days=days)


@app.command()
def discover(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without writing"),
):
    """Discover new repos not yet in projects.yaml."""
    run_discover_cmd(dry_run=dry_run)


@app.command()
def serve():
    """Run MCP server (stdio)."""
    run_serve()


@app.command()
def issue(
    number: Optional[int] = typer.Argument(None, help="Issue number for detail view"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Repository (owner/repo). 'all' for cross-repo."),
    detail: DetailLevel = typer.Option(DetailLevel.standard, "--detail", "-d", help="Detail level"),
    comments: str = typer.Option("3", "--comments", help="Number of comments to show, or 'all'"),
    state: IssueState = typer.Option(IssueState.open, "--state", help="Filter by state (list mode)"),
    limit: int = typer.Option(30, "--limit", help="Max items in list mode"),
    no_pager: bool = typer.Option(False, "--no-pager", help="Disable pager"),
):
    """View issues. Without a number, lists issues. With a number, shows detail."""
    resolved_repo = resolve_repo(repo)
    if number is not None:
        if resolved_repo is None:
            typer.echo("Error: Cannot show issue detail without a repo. Use --repo or run from a git directory.", err=True)
            raise typer.Exit(1)
        run_issue_detail(
            repo=resolved_repo, number=number,
            detail=detail.value, comments=comments, no_pager=no_pager,
        )
    else:
        run_issue_list(
            repo=resolved_repo, state=state.value,
            limit=limit, no_pager=no_pager,
        )


@app.command()
def pr(
    number: Optional[int] = typer.Argument(None, help="PR number for detail view"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="Repository (owner/repo). 'all' for cross-repo."),
    detail: DetailLevel = typer.Option(DetailLevel.standard, "--detail", "-d", help="Detail level"),
    comments: str = typer.Option("3", "--comments", help="Number of comments to show, or 'all'"),
    state: IssueState = typer.Option(IssueState.open, "--state", help="Filter by state (list mode)"),
    limit: int = typer.Option(30, "--limit", help="Max items in list mode"),
    no_pager: bool = typer.Option(False, "--no-pager", help="Disable pager"),
):
    """View pull requests. Without a number, lists PRs. With a number, shows detail."""
    resolved_repo = resolve_repo(repo)
    if number is not None:
        if resolved_repo is None:
            typer.echo("Error: Cannot show PR detail without a repo. Use --repo or run from a git directory.", err=True)
            raise typer.Exit(1)
        run_pr_detail(
            repo=resolved_repo, number=number,
            detail=detail.value, comments=comments, no_pager=no_pager,
        )
    else:
        run_pr_list(
            repo=resolved_repo, state=state.value,
            limit=limit, no_pager=no_pager,
        )


@app.command()
def repo(
    repo_flag: Optional[str] = typer.Option(None, "--repo", "-r", help="Repository (owner/repo)"),
    no_pager: bool = typer.Option(False, "--no-pager", help="Disable pager"),
):
    """Repo-level dashboard — issues, PRs, and activity for one repo."""
    resolved_repo = resolve_repo(repo_flag)
    run_repo_dashboard(repo=resolved_repo, no_pager=no_pager)


def main():
    """Entry point for the ghud CLI."""
    app()
