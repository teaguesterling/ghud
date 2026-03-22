"""CLI argument parsing and command dispatch."""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor

from ghud.config import find_yaml_path, load_repos_from_yaml
from ghud.github import (
    get_username,
    get_notifications,
    get_open_prs,
    get_merged_prs,
    get_issues_for_repos_batch,
)
from ghud.dashboard import render_dashboard


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ghud",
        description="GitHub Heads-Up Display — terminal dashboard for your portfolio repos",
    )
    parser.add_argument("--all", action="store_true", help="Include all notifications")
    parser.add_argument("--days", type=int, default=7, help="Lookback days for merged PRs")

    subparsers = parser.add_subparsers(dest="command")

    discover_parser = subparsers.add_parser("discover", help="Discover new repos")
    discover_parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")

    return parser.parse_args(argv)


def _collect_other_activity(
    notifications: list[dict], portfolio_repos: set[str]
) -> tuple[list[dict], list[dict]]:
    """Split notifications into portfolio and other activity.

    Returns (portfolio_notifications, other_activity_summary).
    """
    portfolio = []
    other: dict[str, dict] = {}

    for n in notifications:
        repo = n.get("repository", {}).get("full_name", "")
        if repo in portfolio_repos:
            portfolio.append(n)
        else:
            if repo not in other:
                other[repo] = {"repo": repo, "count": 0, "reason_set": set()}
            other[repo]["count"] += 1
            other[repo]["reason_set"].add(n.get("reason", "unknown"))

    other_summary = [
        {"repo": v["repo"], "count": v["count"], "reasons": ", ".join(sorted(v["reason_set"]))}
        for v in sorted(other.values(), key=lambda x: x["count"], reverse=True)
    ]
    return portfolio, other_summary


def run_dashboard(args: argparse.Namespace) -> None:
    yaml_path = find_yaml_path()
    if not yaml_path:
        print("Error: Could not find projects.yaml", file=sys.stderr)
        sys.exit(1)

    repos = load_repos_from_yaml(yaml_path)
    portfolio_set = set(repos)
    username = get_username()

    if not username:
        print("Error: Could not determine GitHub username. Run 'gh auth login'.", file=sys.stderr)
        sys.exit(1)

    # Fetch all data concurrently: notifications, PRs, merged PRs, and issues
    with ThreadPoolExecutor(max_workers=4) as pool:
        notif_future = pool.submit(get_notifications)
        prs_future = pool.submit(get_open_prs, username)
        merged_future = pool.submit(get_merged_prs, username, args.days)
        issues_future = pool.submit(get_issues_for_repos_batch, repos, username)

        all_notifications = notif_future.result()
        open_prs = prs_future.result()
        merged_prs = merged_future.result()
        other_issues = issues_future.result()
        other_issues.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

    portfolio_notifications, other_activity = _collect_other_activity(
        all_notifications, portfolio_set
    )

    data = {
        "notifications": portfolio_notifications,
        "open_prs": open_prs,
        "merged_prs": merged_prs,
        "other_issues": other_issues,
        "other_activity": other_activity,
    }

    render_dashboard(data, show_all=args.all)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.command == "discover":
        from ghud.discover import run_discover
        run_discover(args)
    else:
        run_dashboard(args)
