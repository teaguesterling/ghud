"""Wrapper around gh CLI for GitHub API access."""

import json
import subprocess
from datetime import datetime, timedelta, timezone


class GhApiError(RuntimeError):
    """A `gh` invocation failed (auth, rate limit, network, ...).

    Raised instead of silently returning an empty result, so callers can
    distinguish "GitHub said there is nothing" from "we never got an answer".
    An empty list from this module always means a genuinely empty successful
    query.

    `kind` is one of: "auth", "rate_limit", "forbidden", "not_found",
    "network", "missing-gh", "error".
    """

    def __init__(
        self,
        message: str,
        kind: str = "error",
        returncode: int | None = None,
        stderr: str = "",
    ):
        super().__init__(message)
        self.kind = kind
        self.returncode = returncode
        self.stderr = stderr


_NETWORK_MARKERS = (
    "dial tcp",
    "no such host",
    "could not resolve host",
    "connection refused",
    "connection reset",
    "network is unreachable",
    "i/o timeout",
    "temporary failure in name resolution",
    "tls handshake",
    "error connecting",
)


def _classify_gh_failure(returncode: int | None, text: str) -> tuple[str, str]:
    """Map a failed gh invocation to (kind, human-readable summary).

    Order matters: rate-limit stderr also contains "HTTP 403", and network
    "could not resolve host" must not match not-found's "could not resolve to".
    gh reserves exit code 4 for authentication failures.
    """
    t = text.lower()
    if "rate limit" in t or "rate_limited" in t:
        return "rate_limit", "GitHub API rate limit exceeded"
    if (
        "http 401" in t
        or "bad credentials" in t
        or "authentication" in t
        or "gh auth login" in t
        or returncode == 4
    ):
        return "auth", "GitHub authentication failed (try `gh auth login`)"
    if any(marker in t for marker in _NETWORK_MARKERS):
        return "network", "network error talking to GitHub"
    if "could not resolve to" in t or "http 404" in t or "not found" in t:
        return "not_found", "GitHub resource not found"
    if "http 403" in t or "forbidden" in t:
        return "forbidden", "GitHub API request forbidden (HTTP 403)"
    return "error", "gh command failed"


def _gh_failure(
    args: list[str], result: subprocess.CompletedProcess, extra: str = ""
) -> GhApiError:
    """Build a classified GhApiError from a failed gh invocation."""
    stderr = (result.stderr or "").strip()
    text = " ".join(part for part in (stderr, extra) if part)
    kind, summary = _classify_gh_failure(result.returncode, text)
    if text:
        detail = text.splitlines()[0][:300]
    else:
        detail = f"gh exited {result.returncode}"
    return GhApiError(
        f"{summary}: {detail} (gh {' '.join(args[:2])})",
        kind=kind,
        returncode=result.returncode,
        stderr=stderr,
    )


def _run_gh(args: list[str]) -> subprocess.CompletedProcess:
    """Run a gh CLI command and return the result."""
    try:
        return subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise GhApiError(
            "gh CLI not found — install GitHub CLI (https://cli.github.com)",
            kind="missing-gh",
        ) from exc


def _run_gh_json(args: list[str]) -> list | dict:
    """Run a gh CLI command and parse JSON output.

    Raises GhApiError on a non-zero exit so failures (auth, rate limit,
    network) surface instead of masquerading as empty results.
    """
    result = _run_gh(args)
    if result.returncode != 0:
        raise _gh_failure(args, result)
    return json.loads(result.stdout)


def get_username() -> str:
    """Get the authenticated GitHub username.

    Returns "" on failure rather than raising: callers use an empty username
    as the explicit "not authenticated / not configured" signal and print
    their own guidance (see cli.run_dashboard, mcp._get_state).
    """
    result = _run_gh(["api", "user", "--jq", ".login"])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_notifications() -> list[dict]:
    """Get all unread notifications.

    Raises GhApiError on failure; [] means genuinely no notifications.
    """
    # Use --jq to flatten paginated arrays into newline-delimited JSON objects,
    # then parse each line. This avoids the concatenated-arrays issue with --paginate.
    args = ["api", "notifications", "--paginate", "--jq", ".[]"]
    result = _run_gh(args)
    if result.returncode != 0:
        raise _gh_failure(args, result)
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
    """Get PRs authored by the user and *merged* within the lookback window.

    Filters on the merge date (`--merged-at`), not the last-update date: a PR
    merged long ago but commented on yesterday must not reappear as "Recently
    Merged". The server-side filter is re-checked client-side against
    `closedAt` (== merge time for merged PRs, and the search date filter is
    day-granular), and results are ordered newest-merge-first.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    since = cutoff.strftime("%Y-%m-%d")
    prs = _run_gh_json([
        "search", "prs",
        f"--author={username}",
        "--merged",
        f"--merged-at=>={since}",
        "--limit", "50",
        "--json", "title,repository,closedAt,url",
    ])
    recent = []
    for pr in prs:
        closed = pr.get("closedAt", "")
        try:
            merged_at = datetime.fromisoformat(closed.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            # Merged PRs always carry closedAt; keep unparseable entries
            # rather than silently hiding activity (same rationale as
            # data.filter_recent_issues).
            recent.append(pr)
            continue
        if merged_at >= cutoff:
            recent.append(pr)
    recent.sort(key=lambda p: p.get("closedAt", ""), reverse=True)
    return recent


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
    # Build aliased query fragments. owner/name come from config files
    # (~/.mrconfig or projects.yaml); pass them as GraphQL variables so a
    # quote or brace in a config value can never alter the query structure.
    fragments = []
    alias_map = {}
    var_defs = []
    var_args: list[str] = []
    for idx, repo in enumerate(repos):
        parts = repo.split("/")
        if len(parts) != 2:
            continue
        owner, name = parts
        alias = f"r{idx}"
        alias_map[alias] = repo
        var_defs.append(f"$owner{idx}: String!")
        var_defs.append(f"$name{idx}: String!")
        var_args.extend(["-f", f"owner{idx}={owner}", "-f", f"name{idx}={name}"])
        fragments.append(
            f'{alias}: repository(owner: $owner{idx}, name: $name{idx}) {{\n'
            f'  issues(first: 100, states: OPEN, '
            f'orderBy: {{field: CREATED_AT, direction: DESC}}) {{\n'
            f'    nodes {{ number title createdAt url author {{ login }} '
            f'labels(first: 10) {{ nodes {{ name }} }} }}\n'
            f'  }}\n'
            f'}}'
        )

    if not fragments:
        return []

    query = (
        "query(" + ", ".join(var_defs) + ") {\n" + "\n".join(fragments) + "\n}"
    )
    args = ["api", "graphql", "-f", f"query={query}", *var_args]
    result = _run_gh(args)
    # When only some repos in the batch fail (renamed/deleted/private/typo),
    # GitHub GraphQL still returns HTTP 200 with partial `data` plus an
    # `errors` array, and gh exits non-zero. Parse stdout regardless rather
    # than discarding the whole batch — the failed repos surface as null
    # aliases, which the loop below already skips. A failure with no usable
    # `data` at all (rate limit, auth, network) is NOT partial and raises.
    stdout = result.stdout.strip()
    if not stdout:
        if result.returncode != 0:
            raise _gh_failure(args, result)
        return []

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        if result.returncode != 0:
            raise _gh_failure(args, result)
        return []

    if result.returncode != 0 and not data.get("data"):
        gql_errors = " ".join(
            f"{e.get('type', '')} {e.get('message', '')}".strip()
            for e in data.get("errors", [])
            if isinstance(e, dict)
        )
        raise _gh_failure(args, result, extra=gql_errors)

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
    """Get detailed information for a single issue including comments.

    Returns {} when the issue doesn't exist; raises GhApiError for other
    failures (auth, rate limit, network) so they aren't misreported as
    "issue not found".
    """
    try:
        result = _run_gh_json([
            "issue", "view", str(number),
            "--repo", repo,
            "--json", "number,title,state,body,author,createdAt,url,labels,assignees,milestone,comments",
        ])
    except GhApiError as exc:
        if exc.kind == "not_found":
            return {}
        raise
    if isinstance(result, list):
        return {}
    return result


def get_pr_detail(repo: str, number: int) -> dict:
    """Get detailed information for a single PR including comments, reviews, and checks.

    Returns {} when the PR doesn't exist; raises GhApiError for other
    failures (auth, rate limit, network) so they aren't misreported as
    "PR not found".
    """
    try:
        result = _run_gh_json([
            "pr", "view", str(number),
            "--repo", repo,
            "--json", "number,title,state,body,author,createdAt,url,labels,assignees,"
                      "reviewDecision,statusCheckRollup,mergeable,comments,reviews",
        ])
    except GhApiError as exc:
        if exc.kind == "not_found":
            return {}
        raise
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
