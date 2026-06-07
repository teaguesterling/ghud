"""CLI entry point using Typer."""

import sys
from enum import Enum
from typing import Optional

import click
import typer
from typer.core import TyperGroup

from ghud.repo_context import resolve_repo


class AliasGroup(TyperGroup):
    """Typer group that supports command aliases."""

    _aliases = {
        "i": "issue",
        "o": "overview",
        "r": "repo",
    }

    def get_command(self, ctx, cmd_name):
        cmd_name = self._aliases.get(cmd_name, cmd_name)
        return super().get_command(ctx, cmd_name)

    def resolve_command(self, ctx, args):
        if args:
            args[0] = self._aliases.get(args[0], args[0])
        return super().resolve_command(ctx, args)


app = typer.Typer(
    name="ghud",
    help="GitHub Heads-Up Display — terminal dashboard for your portfolio repos",
    invoke_without_command=True,
    cls=AliasGroup,
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


def run_dashboard(show_all: bool = False, days: int = 7, all_repos: bool = False) -> None:
    """Run the overview dashboard (existing behavior)."""
    from ghud.config import resolve_portfolio
    from ghud.github import get_username
    from ghud.data import fetch_dashboard_data
    from ghud.dashboard import render_dashboard

    username = get_username()
    if not username:
        typer.echo("Error: Could not determine GitHub username. Run 'gh auth login'.", err=True)
        raise typer.Exit(1)

    repos, source = resolve_portfolio(focused=not all_repos, username=username)
    if not source:
        typer.echo("Error: no portfolio found (~/.mrconfig or projects.yaml)", err=True)
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
    all_repos: bool = False,
) -> None:
    """Fetch and render the issue list."""
    from ghud.render_issue import render_issue_list
    from ghud.pager import render_with_pager

    if repo is not None:
        from ghud.github import get_issues_for_repo
        issues = get_issues_for_repo(repo)
        # TODO: support --state closed|all by adding state param to get_issues_for_repo
    else:
        from ghud.config import resolve_portfolio
        from ghud.github import get_issues_for_repos_batch, get_username
        username = get_username()
        repos, source = resolve_portfolio(focused=not all_repos, username=username)
        if not source:
            typer.echo("Error: no portfolio found (~/.mrconfig or projects.yaml)", err=True)
            raise typer.Exit(1)
        issues = get_issues_for_repos_batch(repos, exclude_author=username)
        issues.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

    issues = issues[:limit]

    def _render(console):
        render_issue_list(issues, repo=repo, console=console)

    render_with_pager(_render, no_pager=no_pager)


def run_issue_detail(
    repo: str,
    number: int,
    detail: str = "standard",
    comments: str = "3",
    no_pager: bool = False,
) -> None:
    """Fetch and render issue detail."""
    from ghud.github import get_issue_detail
    from ghud.render_issue import render_issue_detail
    from ghud.pager import render_with_pager

    issue = get_issue_detail(repo, number)
    if not issue:
        typer.echo(f"Error: Could not find issue #{number} in {repo}", err=True)
        raise typer.Exit(1)

    max_comments = None if comments == "all" else int(comments)

    def _render(console):
        render_issue_detail(
            issue, repo=repo, detail=detail,
            max_comments=max_comments, console=console,
        )

    render_with_pager(_render, no_pager=no_pager)


def run_pr_list(
    repo: str | None = None,
    state: str = "open",
    limit: int = 30,
    no_pager: bool = False,
) -> None:
    """Fetch and render the PR list."""
    from ghud.render_pr import render_pr_list
    from ghud.pager import render_with_pager

    if repo is not None:
        from ghud.github import get_prs_for_repo
        prs = get_prs_for_repo(repo, state=state, limit=limit)
    else:
        from ghud.github import get_open_prs, get_username
        username = get_username()
        if not username:
            typer.echo("Error: Could not determine GitHub username.", err=True)
            raise typer.Exit(1)
        prs = get_open_prs(username)
        prs = prs[:limit]

    def _render(console):
        render_pr_list(prs, repo=repo, console=console)

    render_with_pager(_render, no_pager=no_pager)


def run_pr_detail(
    repo: str,
    number: int,
    detail: str = "standard",
    comments: str = "3",
    no_pager: bool = False,
) -> None:
    """Fetch and render PR detail."""
    from ghud.github import get_pr_detail
    from ghud.render_pr import render_pr_detail
    from ghud.pager import render_with_pager

    pr = get_pr_detail(repo, number)
    if not pr:
        typer.echo(f"Error: Could not find PR #{number} in {repo}", err=True)
        raise typer.Exit(1)

    max_comments = None if comments == "all" else int(comments)

    def _render(console):
        render_pr_detail(
            pr, repo=repo, detail=detail,
            max_comments=max_comments, console=console,
        )

    render_with_pager(_render, no_pager=no_pager)


def run_repo_dashboard(
    repo: str | None = None,
    no_pager: bool = False,
) -> None:
    """Fetch and render the repo dashboard."""
    from ghud.github import get_issues_for_repo, get_prs_for_repo
    from ghud.render_repo import render_repo_dashboard
    from ghud.pager import render_with_pager

    if repo is None:
        typer.echo("Error: Cannot show repo dashboard without a repo. Use --repo or run from a git directory.", err=True)
        raise typer.Exit(1)

    issues = get_issues_for_repo(repo)
    prs = get_prs_for_repo(repo, state="open", limit=30)

    data = {"issues": issues, "prs": prs}

    def _render(console):
        render_repo_dashboard(data, repo=repo, console=console)

    render_with_pager(_render, no_pager=no_pager)


@app.callback(invoke_without_command=True)
def default(
    ctx: typer.Context,
    show_all: bool = typer.Option(False, "--all", help="Include all notifications"),
    days: int = typer.Option(7, "--days", help="Lookback days for merged PRs and new issues"),
    all_repos: bool = typer.Option(
        False, "--all-repos", help="Use the full manifest, not just your focused repos"
    ),
):
    """GitHub Heads-Up Display."""
    if ctx.invoked_subcommand is None:
        run_dashboard(show_all=show_all, days=days, all_repos=all_repos)


@app.command()
def overview(
    show_all: bool = typer.Option(False, "--all", help="Include all notifications"),
    days: int = typer.Option(7, "--days", help="Lookback days for merged PRs and new issues"),
    all_repos: bool = typer.Option(
        False, "--all-repos", help="Use the full manifest, not just your focused repos"
    ),
):
    """Global dashboard — notifications, PRs, issues across portfolio repos."""
    run_dashboard(show_all=show_all, days=days, all_repos=all_repos)


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
    all_repos: bool = typer.Option(
        False, "--all-repos", help="List mode: use the full manifest, not just your focused repos"
    ),
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
            limit=limit, no_pager=no_pager, all_repos=all_repos,
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
