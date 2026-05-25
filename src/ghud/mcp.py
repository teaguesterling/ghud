# src/ghud/mcp.py
"""MCP server exposing ghud tools for AI agents."""

from fastmcp import FastMCP

from ghud.config import resolve_portfolio
from ghud.github import (
    get_username,
    get_notifications,
    get_open_prs,
    get_merged_prs,
    get_issues_for_repos_batch,
)
from ghud.data import (
    fetch_dashboard_data,
    collect_other_activity,
    filter_important_notifications,
)
from ghud.dashboard import render_dashboard_markdown
from ghud.discover import fetch_all_user_repos, find_new_repos

# Lazy-initialized state — resolved on first tool call, not at import time.
# This avoids subprocess calls during test collection or module import.
_state: dict | None = None


def _get_state() -> dict:
    """Resolve config and username once, cache for subsequent calls."""
    global _state
    if _state is None:
        username = get_username()
        repos, _source = resolve_portfolio(username=username)
        _state = {"repos": repos, "username": username}
    return _state


mcp = FastMCP("ghud", instructions="GitHub Heads-Up Display — portfolio dashboard tools")


@mcp.tool()
def get_dashboard(show_all: bool = False, days: int = 7) -> str:
    """Get the full GitHub dashboard as formatted markdown.

    Shows notifications, open PRs, recently merged PRs, issues from others,
    and other activity across portfolio repos.
    """
    state = _get_state()
    if not state["repos"] or not state["username"]:
        return "Error: ghud not configured (missing projects.yaml or gh auth)"
    data = fetch_dashboard_data(state["repos"], state["username"], days=days)
    return render_dashboard_markdown(data, show_all=show_all)


@mcp.tool()
def get_notifications_tool(important_only: bool = True) -> list[dict]:
    """Get GitHub notifications for portfolio repos.

    By default returns only important notifications (review_requested, mention,
    assign, team_mention, security_alert). Set important_only=False for all.
    """
    state = _get_state()
    all_notifs = get_notifications()
    portfolio, _ = collect_other_activity(all_notifs, set(state["repos"]))
    return filter_important_notifications(portfolio, important_only=important_only)


@mcp.tool()
def get_open_prs_tool() -> list[dict]:
    """Get your open pull requests across all repos.

    Returns raw API fields: title, repository, state, createdAt, updatedAt,
    url, commentsCount.
    """
    state = _get_state()
    if not state["username"]:
        return []
    return get_open_prs(state["username"])


@mcp.tool()
def get_merged_prs_tool(days: int = 7) -> list[dict]:
    """Get your recently merged pull requests.

    Returns PRs merged within the lookback window (default 7 days).
    """
    state = _get_state()
    if not state["username"]:
        return []
    return get_merged_prs(state["username"], days=days)


@mcp.tool()
def get_issues_from_others() -> list[dict]:
    """Get open issues on portfolio repos created by other people.

    Excludes issues you authored. Returns issues with repo, title, author,
    createdAt, url, labels.
    """
    state = _get_state()
    if not state["repos"] or not state["username"]:
        return []
    issues = get_issues_for_repos_batch(state["repos"], exclude_author=state["username"])
    issues.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return issues


@mcp.tool()
def get_portfolio_repos() -> list[str]:
    """Get the list of portfolio repos from projects.yaml."""
    return _get_state()["repos"]


@mcp.tool()
def discover_repos() -> list[dict]:
    """Find GitHub repos not yet tracked in projects.yaml.

    Returns a list of repos with nameWithOwner, name, description, and fork status.
    Does not modify projects.yaml.
    """
    state = _get_state()
    if not state["username"]:
        return []
    github_repos = fetch_all_user_repos(state["username"])
    return find_new_repos(github_repos, state["repos"])


def main():
    """Entry point for ghud-mcp script."""
    mcp.run()
