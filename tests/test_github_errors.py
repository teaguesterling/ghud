# tests/test_github_errors.py
"""Regression tests for issue #2: gh failures must surface as errors (not
"no activity"), "Recently Merged" must filter on merge date, and GraphQL
owner/name must be parameterized.

All tests mock the `gh` subprocess boundary so they run offline.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from ghud.github import (
    get_notifications,
    get_open_prs,
    get_merged_prs,
    get_issues_for_repos_batch,
)


def _mock_run(stdout_data, returncode=0, stderr=""):
    """Mock subprocess.run returning fixed stdout/stderr/returncode."""
    def mock(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, returncode)
        result.stdout = stdout_data if isinstance(stdout_data, str) else json.dumps(stdout_data)
        result.stderr = stderr
        return result
    return mock


def _capture_run(captured, stdout_data, returncode=0, stderr=""):
    """Like _mock_run but records the gh command line into `captured`."""
    def mock(cmd, **kwargs):
        captured.append(list(cmd))
        result = subprocess.CompletedProcess(cmd, returncode)
        result.stdout = stdout_data if isinstance(stdout_data, str) else json.dumps(stdout_data)
        result.stderr = stderr
        return result
    return mock


RATE_LIMIT_STDERR = (
    "HTTP 403: API rate limit exceeded for 203.0.113.7. "
    "(https://api.github.com/search/issues?q=...)"
)
AUTH_STDERR = "HTTP 401: Bad credentials (https://api.github.com/notifications)"
NETWORK_STDERR = (
    'error connecting to api.github.com\n'
    'dial tcp: lookup api.github.com: no such host'
)


# ---------------------------------------------------------------------------
# Bug 1 — silent API failure must NOT render as an empty ("no activity") result
# ---------------------------------------------------------------------------

def test_rate_limited_search_is_not_silently_empty(monkeypatch):
    """A rate-limited (403) gh run must surface an error, not return []."""
    monkeypatch.setattr(
        subprocess, "run", _mock_run("", returncode=1, stderr=RATE_LIMIT_STDERR)
    )
    try:
        result = get_open_prs("testuser")
    except Exception as exc:
        assert type(exc).__name__ == "GhApiError"
        assert exc.kind == "rate_limit"
        assert "rate limit" in str(exc).lower()
    else:
        pytest.fail(
            f"rate-limited gh exit was swallowed to {result!r} — "
            "indistinguishable from a genuinely empty result"
        )


def test_unauthenticated_run_raises_auth_error(monkeypatch):
    from ghud.github import GhApiError

    monkeypatch.setattr(
        subprocess, "run", _mock_run("", returncode=1, stderr=AUTH_STDERR)
    )
    with pytest.raises(GhApiError) as exc_info:
        get_open_prs("testuser")
    assert exc_info.value.kind == "auth"


def test_gh_auth_exit_code_4_raises_auth_error(monkeypatch):
    """gh reserves exit code 4 for authentication failures."""
    from ghud.github import GhApiError

    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("", returncode=4,
                  stderr="To get started with GitHub CLI, please run:  gh auth login"),
    )
    with pytest.raises(GhApiError) as exc_info:
        get_open_prs("testuser")
    assert exc_info.value.kind == "auth"


def test_network_failure_raises_network_error(monkeypatch):
    from ghud.github import GhApiError

    monkeypatch.setattr(
        subprocess, "run", _mock_run("", returncode=1, stderr=NETWORK_STDERR)
    )
    with pytest.raises(GhApiError) as exc_info:
        get_open_prs("testuser")
    assert exc_info.value.kind == "network"


def test_notifications_failure_raises(monkeypatch):
    from ghud.github import GhApiError

    monkeypatch.setattr(
        subprocess, "run", _mock_run("", returncode=1, stderr=RATE_LIMIT_STDERR)
    )
    with pytest.raises(GhApiError) as exc_info:
        get_notifications()
    assert exc_info.value.kind == "rate_limit"


def test_graphql_total_failure_raises(monkeypatch):
    """A GraphQL run with no usable data (rate limit / auth / network) must
    raise, unlike a partial-batch failure which returns the good repos."""
    from ghud.github import GhApiError

    monkeypatch.setattr(
        subprocess, "run", _mock_run("", returncode=1, stderr=RATE_LIMIT_STDERR)
    )
    with pytest.raises(GhApiError) as exc_info:
        get_issues_for_repos_batch(["org/repo-a"], exclude_author="me")
    assert exc_info.value.kind == "rate_limit"


def test_graphql_rate_limited_error_payload_raises(monkeypatch):
    """GraphQL rate limits come back as HTTP 200 + data:null + RATE_LIMITED."""
    from ghud.github import GhApiError

    payload = {
        "data": None,
        "errors": [{"type": "RATE_LIMITED", "message": "API rate limit exceeded"}],
    }
    monkeypatch.setattr(subprocess, "run", _mock_run(payload, returncode=1))
    with pytest.raises(GhApiError) as exc_info:
        get_issues_for_repos_batch(["org/repo-a"], exclude_author="me")
    assert exc_info.value.kind == "rate_limit"


def test_discover_fetch_failure_raises(monkeypatch):
    """A failed repo fetch must not be reported as 'all repos tracked'."""
    from ghud.discover import fetch_all_user_repos
    from ghud.github import GhApiError

    monkeypatch.setattr(
        subprocess, "run", _mock_run("", returncode=1, stderr=RATE_LIMIT_STDERR)
    )
    with pytest.raises(GhApiError) as exc_info:
        fetch_all_user_repos("testuser")
    assert exc_info.value.kind == "rate_limit"


def test_dashboard_data_failure_is_not_all_empty(monkeypatch):
    """The dashboard fetch must not turn an API failure into all-empty data,
    which downstream renders as 'No activity to show.'"""
    from ghud.data import fetch_dashboard_data

    monkeypatch.setattr(
        subprocess, "run", _mock_run("", returncode=1, stderr=RATE_LIMIT_STDERR)
    )
    try:
        data = fetch_dashboard_data(["org/repo"], "testuser", days=7)
    except Exception:
        return  # surfaced as an error: correct
    all_empty = not any([
        data["notifications"], data["open_prs"], data["merged_prs"],
        data["other_issues"], data["other_activity"],
    ])
    assert not all_empty, (
        "API failure produced an all-empty dashboard, indistinguishable "
        "from a genuinely quiet portfolio"
    )


def test_cli_main_reports_gh_api_error(monkeypatch, capsys):
    """The CLI entry point turns a GhApiError into a message + exit 1,
    not a traceback."""
    import ghud.cli as cli
    from ghud.github import GhApiError

    def boom(**kwargs):
        raise GhApiError("GitHub API rate limit exceeded", kind="rate_limit")

    monkeypatch.setattr(sys, "argv", ["ghud"])
    monkeypatch.setattr(cli, "run_dashboard", boom)
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert "rate limit" in err.lower()
    assert "No activity" not in err


# ---------------------------------------------------------------------------
# Bug 2 — "Recently Merged" must filter on merge date, not last-update date
# ---------------------------------------------------------------------------

def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_merged_prs_exclude_stale_merges_updated_recently(monkeypatch):
    """A PR merged 400 days ago but commented on yesterday matches an
    `--updated` filter; it must NOT appear in Recently Merged."""
    now = datetime.now(timezone.utc)
    stale = {
        "title": "Merged long ago, commented yesterday",
        "repository": {"nameWithOwner": "org/repo"},
        "closedAt": _iso(now - timedelta(days=400)),
        "url": "https://example/1",
    }
    fresh = {
        "title": "Merged two days ago",
        "repository": {"nameWithOwner": "org/repo"},
        "closedAt": _iso(now - timedelta(days=2)),
        "url": "https://example/2",
    }
    # Simulate GitHub's response to an update-date filter: both PRs were
    # updated recently, so both come back. Only the actually-recently-merged
    # one may survive.
    monkeypatch.setattr(subprocess, "run", _mock_run([stale, fresh]))
    result = get_merged_prs("testuser", days=7)
    titles = [pr["title"] for pr in result]
    assert titles == ["Merged two days ago"], titles


def test_merged_prs_query_filters_on_merge_date(monkeypatch):
    """The gh search must constrain the *merge* date (--merged-at), not the
    last-update date (--updated)."""
    captured: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", _capture_run(captured, []))
    get_merged_prs("testuser", days=7)
    assert captured, "gh was not invoked"
    args = captured[0]
    assert any(a.startswith("--merged-at") for a in args), args
    assert not any(a.startswith("--updated") for a in args), args


def test_merged_prs_sorted_newest_merge_first(monkeypatch):
    now = datetime.now(timezone.utc)
    older = {
        "title": "Merged five days ago",
        "repository": {"nameWithOwner": "org/repo"},
        "closedAt": _iso(now - timedelta(days=5)),
        "url": "https://example/1",
    }
    newer = {
        "title": "Merged yesterday",
        "repository": {"nameWithOwner": "org/repo"},
        "closedAt": _iso(now - timedelta(days=1)),
        "url": "https://example/2",
    }
    monkeypatch.setattr(subprocess, "run", _mock_run([older, newer]))
    result = get_merged_prs("testuser", days=7)
    assert [pr["title"] for pr in result] == [
        "Merged yesterday", "Merged five days ago",
    ]


# ---------------------------------------------------------------------------
# Bug 3 — GraphQL owner/name must be parameterized, not interpolated
# ---------------------------------------------------------------------------

GRAPHQL_EMPTY = {"data": {"r0": {"issues": {"nodes": []}}}}


def test_graphql_owner_name_not_interpolated(monkeypatch):
    """A config-supplied owner/name containing GraphQL-significant characters
    must not appear inside the query text (passed as variables instead)."""
    captured: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", _capture_run(captured, GRAPHQL_EMPTY))
    hostile_owner = 'own"er) { viewer { login } } #'
    hostile_name = 'na"me'
    get_issues_for_repos_batch([f"{hostile_owner}/{hostile_name}"])
    args = captured[0]
    query = next(a for a in args if isinstance(a, str) and a.startswith("query="))
    assert hostile_owner not in query, "owner interpolated into query text"
    assert hostile_name not in query, "name interpolated into query text"
    assert f"owner0={hostile_owner}" in args
    assert f"name0={hostile_name}" in args


def test_graphql_uses_variables_for_owner_and_name(monkeypatch):
    captured: list[list[str]] = []
    monkeypatch.setattr(subprocess, "run", _capture_run(captured, GRAPHQL_EMPTY))
    get_issues_for_repos_batch(["org/repo-a"])
    args = captured[0]
    query = next(a for a in args if isinstance(a, str) and a.startswith("query="))
    assert "repository(owner: $owner0, name: $name0)" in query
    assert "$owner0: String!" in query
    assert "$name0: String!" in query
    assert "owner0=org" in args
    assert "name0=repo-a" in args


def test_graphql_results_still_parse_with_variables(monkeypatch):
    """The parameterized query still maps aliases back to repos correctly."""
    payload = {
        "data": {
            "r0": {"issues": {"nodes": [
                {"number": 7, "title": "Bug", "createdAt": "2026-06-30T00:00:00Z",
                 "url": "https://example/7", "author": {"login": "other"},
                 "labels": {"nodes": [{"name": "bug"}]}},
            ]}},
        }
    }
    monkeypatch.setattr(subprocess, "run", _mock_run(payload))
    result = get_issues_for_repos_batch(["org/repo-a"], exclude_author="me")
    assert len(result) == 1
    assert result[0]["repo"] == "org/repo-a"
    assert result[0]["labels"] == [{"name": "bug"}]
