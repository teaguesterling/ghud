# src/ghud/data.py
"""Shared data-fetching and filtering logic."""

from concurrent.futures import ThreadPoolExecutor

from ghud.github import (
    get_notifications,
    get_open_prs,
    get_merged_prs,
    get_issues_for_repos_batch,
)

IMPORTANT_REASONS = {"review_requested", "mention", "assign", "team_mention", "security_alert"}


def collect_other_activity(
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


def filter_important_notifications(
    notifications: list[dict], important_only: bool = True
) -> list[dict]:
    """Filter notifications to important ones only."""
    if not important_only:
        return notifications
    return [n for n in notifications if n.get("reason") in IMPORTANT_REASONS]


def fetch_dashboard_data(
    repos: list[str], username: str, days: int = 7
) -> dict:
    """Fetch all dashboard data concurrently. Returns data dict."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        notif_future = pool.submit(get_notifications)
        prs_future = pool.submit(get_open_prs, username)
        merged_future = pool.submit(get_merged_prs, username, days)
        issues_future = pool.submit(get_issues_for_repos_batch, repos, username)

        all_notifications = notif_future.result()
        open_prs = prs_future.result()
        merged_prs = merged_future.result()
        other_issues = issues_future.result()
        other_issues.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

    portfolio_notifications, other_activity = collect_other_activity(
        all_notifications, set(repos)
    )

    return {
        "notifications": portfolio_notifications,
        "open_prs": open_prs,
        "merged_prs": merged_prs,
        "other_issues": other_issues,
        "other_activity": other_activity,
    }
