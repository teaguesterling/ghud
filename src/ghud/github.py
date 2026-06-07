"""Wrapper around gh CLI for GitHub API access."""

import json
import subprocess
from datetime import datetime, timedelta, timezone


def _run_gh(args: list[str]) -> subprocess.CompletedProcess:
    """Run a gh CLI command and return the result."""
    return subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
    )


def _run_gh_json(args: list[str]) -> list | dict:
    """Run a gh CLI command and parse JSON output."""
    result = _run_gh(args)
    if result.returncode != 0:
        return []
    return json.loads(result.stdout)


def get_username() -> str:
    """Get the authenticated GitHub username."""
    result = _run_gh(["api", "user", "--jq", ".login"])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_notifications() -> list[dict]:
    """Get all unread notifications."""
    # Use --jq to flatten paginated arrays into newline-delimited JSON objects,
    # then parse each line. This avoids the concatenated-arrays issue with --paginate.
    result = _run_gh(["api", "notifications", "--paginate", "--jq", ".[]"])
    if result.returncode != 0:
        return []
    items = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if line:
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return items


def get_open_prs(username: str) -> list[dict]:
    """Get open PRs authored by the user."""
    return _run_gh_json([
        "search", "prs",
        f"--author={username}",
        "--state=open",
        "--limit", "100",
        "--json", "number,title,repository,state,updatedAt,url,commentsCount,createdAt",
    ])


def get_merged_prs(username: str, days: int = 7) -> list[dict]:
    """Get PRs merged by the user within the lookback window."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    return _run_gh_json([
        "search", "prs",
        f"--author={username}",
        "--merged",
        f"--updated=>={since}",
        "--sort=updated",
        "--limit", "50",
        "--json", "title,repository,closedAt,url",
    ])


def get_issues_for_repo(repo: str, exclude_author: str = "") -> list[dict]:
    """Get open issues for a repo, optionally excluding an author."""
    data = _run_gh_json([
        "issue", "list",
        "--repo", repo,
        "--state", "open",
        "--limit", "100",
        "--json", "number,title,author,createdAt,url,labels",
    ])
    if exclude_author and isinstance(data, list):
        data = [
            issue for issue in data
            if (issue.get("author") or {}).get("login") != exclude_author
        ]
    return data


def get_issues_for_repos_batch(
    repos: list[str], exclude_author: str = ""
) -> list[dict]:
    """Fetch open issues for all repos in a single GraphQL query.

    Batches repos into groups of 25 (GraphQL complexity limit) and returns
    a flat list of issues, each with a 'repo' field added.
    """
    all_issues = []
    batch_size = 25

    for i in range(0, len(repos), batch_size):
        batch = repos[i:i + batch_size]
        issues = _graphql_issues_batch(batch, exclude_author)
        all_issues.extend(issues)

    return all_issues


def _graphql_issues_batch(
    repos: list[str], exclude_author: str = ""
) -> list[dict]:
    """Execute a single GraphQL query to fetch issues for a batch of repos."""
    # Build aliased query fragments
    fragments = []
    alias_map = {}
    for idx, repo in enumerate(repos):
        parts = repo.split("/")
        if len(parts) != 2:
            continue
        owner, name = parts
        alias = f"r{idx}"
        alias_map[alias] = repo
        fragments.append(
            f'{alias}: repository(owner: "{owner}", name: "{name}") {{\n'
            f'  issues(first: 100, states: OPEN, '
            f'orderBy: {{field: CREATED_AT, direction: DESC}}) {{\n'
            f'    nodes {{ number title createdAt url author {{ login }} '
            f'labels(first: 10) {{ nodes {{ name }} }} }}\n'
            f'  }}\n'
            f'}}'
        )

    if not fragments:
        return []

    query = "query {\n" + "\n".join(fragments) + "\n}"
    result = _run_gh(["api", "graphql", "-f", f"query={query}"])
    # When only some repos in the batch fail (renamed/deleted/private/typo),
    # GitHub GraphQL still returns HTTP 200 with partial `data` plus an
    # `errors` array, and gh exits non-zero. Parse stdout regardless rather
    # than discarding the whole batch — the failed repos surface as null
    # aliases, which the loop below already skips.
    if not result.stdout.strip():
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    issues = []
    for alias, repo in alias_map.items():
        repo_data = data.get("data", {}).get(alias)
        if not repo_data:
            continue
        for node in repo_data.get("issues", {}).get("nodes", []):
            # Normalize to match REST API format
            # author is null for issues opened by since-deleted accounts
            author_login = (node.get("author") or {}).get("login", "")
            if exclude_author and author_login == exclude_author:
                continue
            labels = [
                {"name": l["name"]}
                for l in node.get("labels", {}).get("nodes", [])
            ]
            issues.append({
                "number": node.get("number"),
                "title": node.get("title", ""),
                "author": {"login": author_login},
                "createdAt": node.get("createdAt", ""),
                "url": node.get("url", ""),
                "labels": labels,
                "repo": repo,
            })

    return issues


def get_issue_detail(repo: str, number: int) -> dict:
    """Get detailed information for a single issue including comments."""
    result = _run_gh_json([
        "issue", "view", str(number),
        "--repo", repo,
        "--json", "number,title,state,body,author,createdAt,url,labels,assignees,milestone,comments",
    ])
    if isinstance(result, list):
        return {}
    return result


def get_pr_detail(repo: str, number: int) -> dict:
    """Get detailed information for a single PR including comments, reviews, and checks."""
    result = _run_gh_json([
        "pr", "view", str(number),
        "--repo", repo,
        "--json", "number,title,state,body,author,createdAt,url,labels,assignees,"
                  "reviewDecision,statusCheckRollup,mergeable,comments,reviews",
    ])
    if isinstance(result, list):
        return {}
    return result


def get_prs_for_repo(repo: str, state: str = "open", limit: int = 30) -> list[dict]:
    """Get PRs for a repo with state filter."""
    return _run_gh_json([
        "pr", "list",
        "--repo", repo,
        "--state", state,
        "--limit", str(limit),
        "--json", "number,title,author,createdAt,url,state,statusCheckRollup,reviewDecision",
    ])
