import json
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
from ghud.github import (
    GhApiError,
    get_username,
    get_notifications,
    get_open_prs,
    get_merged_prs,
    get_issues_for_repo,
    get_issues_for_repos_batch,
    get_issue_detail,
    get_pr_detail,
    get_prs_for_repo,
)


def _mock_run(stdout_data, returncode=0, stderr=""):
    """Create a mock for subprocess.run that returns given stdout."""
    def mock(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, returncode)
        result.stdout = stdout_data if isinstance(stdout_data, str) else json.dumps(stdout_data)
        result.stderr = stderr
        return result
    return mock


def test_get_username(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _mock_run("testuser\n"))
    assert get_username() == "testuser"


def test_get_notifications(monkeypatch):
    # Notifications use --jq '.[]' which outputs one JSON object per line
    obj = {"reason": "review_requested", "subject": {"title": "Fix bug", "type": "PullRequest"},
           "repository": {"full_name": "org/repo"}}
    monkeypatch.setattr(subprocess, "run", _mock_run(json.dumps(obj)))
    result = get_notifications()
    assert len(result) == 1
    assert result[0]["reason"] == "review_requested"


def test_get_open_prs(monkeypatch):
    data = [
        {"title": "My PR", "repository": {"nameWithOwner": "org/repo"},
         "state": "open", "updatedAt": "2026-03-22T00:00:00Z", "url": "https://..."},
    ]
    monkeypatch.setattr(subprocess, "run", _mock_run(data))
    result = get_open_prs("testuser")
    assert len(result) == 1


def test_get_merged_prs(monkeypatch):
    closed = (datetime.now(timezone.utc) - timedelta(days=2)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    data = [
        {"title": "Merged PR", "repository": {"nameWithOwner": "org/repo"},
         "closedAt": closed, "url": "https://..."},
    ]
    monkeypatch.setattr(subprocess, "run", _mock_run(data))
    result = get_merged_prs("testuser", days=7)
    assert len(result) == 1


def test_get_issues_for_repo(monkeypatch):
    data = [
        {"number": 1, "title": "Bug", "author": {"login": "other"},
         "createdAt": "2026-03-20T00:00:00Z", "url": "https://..."},
        {"number": 2, "title": "My issue", "author": {"login": "me"},
         "createdAt": "2026-03-21T00:00:00Z", "url": "https://..."},
    ]
    monkeypatch.setattr(subprocess, "run", _mock_run(data))
    result = get_issues_for_repo("org/repo", exclude_author="me")
    assert len(result) == 1
    assert result[0]["title"] == "Bug"


def test_get_username_returns_empty_on_failure(monkeypatch):
    monkeypatch.setattr(subprocess, "run", _mock_run("", returncode=1))
    assert get_username() == ""


def test_get_issues_for_repos_batch(monkeypatch):
    graphql_response = {
        "data": {
            "r0": {"issues": {"nodes": [
                {"number": 1, "title": "Bug", "createdAt": "2026-03-20T00:00:00Z",
                 "url": "https://...", "author": {"login": "other"},
                 "labels": {"nodes": [{"name": "bug"}]}},
                {"number": 2, "title": "My issue", "createdAt": "2026-03-21T00:00:00Z",
                 "url": "https://...", "author": {"login": "me"},
                 "labels": {"nodes": []}},
            ]}},
            "r1": {"issues": {"nodes": [
                {"number": 5, "title": "Feature req", "createdAt": "2026-03-19T00:00:00Z",
                 "url": "https://...", "author": {"login": "someone"},
                 "labels": {"nodes": []}},
            ]}},
        }
    }
    monkeypatch.setattr(subprocess, "run", _mock_run(graphql_response))
    result = get_issues_for_repos_batch(["org/repo-a", "org/repo-b"], exclude_author="me")
    # Should exclude "My issue" (author=me), keep the other 2
    assert len(result) == 2
    titles = {r["title"] for r in result}
    assert "Bug" in titles
    assert "Feature req" in titles
    assert result[0]["repo"] in ("org/repo-a", "org/repo-b")


def test_get_issues_for_repos_batch_null_author(monkeypatch):
    # Issues from since-deleted accounts have author: null — must not crash.
    graphql_response = {
        "data": {
            "r0": {"issues": {"nodes": [
                {"number": 1, "title": "Ghost issue", "createdAt": "2026-03-20T00:00:00Z",
                 "url": "https://...", "author": None,
                 "labels": {"nodes": []}},
            ]}},
        }
    }
    monkeypatch.setattr(subprocess, "run", _mock_run(graphql_response))
    result = get_issues_for_repos_batch(["org/repo-a"], exclude_author="me")
    assert len(result) == 1
    assert result[0]["title"] == "Ghost issue"


def test_get_issues_for_repos_batch_partial_failure(monkeypatch):
    # One repo in the batch is invalid: GitHub returns partial data + errors
    # and gh exits non-zero. The good repo's issues must still come through.
    graphql_response = {
        "data": {
            "r0": {"issues": {"nodes": [
                {"number": 1, "title": "Real bug", "createdAt": "2026-03-20T00:00:00Z",
                 "url": "https://...", "author": {"login": "other"},
                 "labels": {"nodes": []}},
            ]}},
            "r1": None,
        },
        "errors": [{"message": "Could not resolve to a Repository with the name 'org/gone'."}],
    }
    monkeypatch.setattr(subprocess, "run", _mock_run(graphql_response, returncode=1))
    result = get_issues_for_repos_batch(["org/repo-a", "org/gone"], exclude_author="me")
    assert len(result) == 1
    assert result[0]["title"] == "Real bug"


def test_get_issues_for_repos_batch_empty_stdout(monkeypatch):
    # A true failure (no stdout at all) must raise, not silently return [].
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("", returncode=1, stderr="HTTP 403: API rate limit exceeded"),
    )
    with pytest.raises(GhApiError):
        get_issues_for_repos_batch(["org/repo-a"], exclude_author="me")


def test_get_issue_detail(monkeypatch):
    data = {
        "number": 42,
        "title": "Fix the thing",
        "state": "open",
        "body": "## Description\nThis needs fixing.",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "url": "https://github.com/org/repo/issues/42",
        "labels": [{"name": "bug"}],
        "assignees": [{"login": "bob"}],
        "milestone": {"title": "v2.0"},
        "comments": [
            {"author": {"login": "carol"}, "body": "I can reproduce.",
             "createdAt": "2026-03-21T00:00:00Z"},
            {"author": {"login": "dave"}, "body": "Working on a fix.",
             "createdAt": "2026-03-22T00:00:00Z"},
        ],
    }
    monkeypatch.setattr(subprocess, "run", _mock_run(data))
    result = get_issue_detail("org/repo", 42)
    assert result["number"] == 42
    assert result["title"] == "Fix the thing"
    assert result["body"] == "## Description\nThis needs fixing."
    assert len(result["comments"]) == 2
    assert result["labels"][0]["name"] == "bug"


def test_get_issue_detail_not_found(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("", returncode=1,
                  stderr="GraphQL: Could not resolve to an issue or pull "
                         "request with the number of 999. (repository.issue)"),
    )
    result = get_issue_detail("org/repo", 999)
    assert result == {}


def test_get_issue_detail_api_failure_raises(monkeypatch):
    # A rate-limited fetch must not be misreported as "issue not found".
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("", returncode=1, stderr="HTTP 403: API rate limit exceeded"),
    )
    with pytest.raises(GhApiError):
        get_issue_detail("org/repo", 42)


def test_get_pr_detail(monkeypatch):
    data = {
        "number": 15,
        "title": "Add feature X",
        "state": "OPEN",
        "body": "This PR adds feature X.",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "url": "https://github.com/org/repo/pull/15",
        "labels": [{"name": "enhancement"}],
        "assignees": [{"login": "bob"}],
        "reviewDecision": "APPROVED",
        "statusCheckRollup": [
            {"name": "ci/build", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "ci/lint", "status": "COMPLETED", "conclusion": "SUCCESS"},
        ],
        "mergeable": "MERGEABLE",
        "comments": [
            {"author": {"login": "carol"}, "body": "LGTM!",
             "createdAt": "2026-03-21T00:00:00Z"},
        ],
        "reviews": [
            {"author": {"login": "carol"}, "state": "APPROVED",
             "body": "", "submittedAt": "2026-03-21T00:00:00Z"},
        ],
    }
    monkeypatch.setattr(subprocess, "run", _mock_run(data))
    result = get_pr_detail("org/repo", 15)
    assert result["number"] == 15
    assert result["reviewDecision"] == "APPROVED"
    assert len(result["statusCheckRollup"]) == 2


def test_get_pr_detail_not_found(monkeypatch):
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("", returncode=1,
                  stderr="GraphQL: Could not resolve to a PullRequest with "
                         "the number of 999. (repository.pullRequest)"),
    )
    result = get_pr_detail("org/repo", 999)
    assert result == {}


def test_get_prs_for_repo(monkeypatch):
    data = [
        {"number": 10, "title": "PR A", "author": {"login": "alice"},
         "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
         "state": "OPEN", "statusCheckRollup": [], "reviewDecision": ""},
        {"number": 11, "title": "PR B", "author": {"login": "bob"},
         "createdAt": "2026-03-21T00:00:00Z", "url": "https://...",
         "state": "OPEN", "statusCheckRollup": [], "reviewDecision": "APPROVED"},
    ]
    monkeypatch.setattr(subprocess, "run", _mock_run(data))
    result = get_prs_for_repo("org/repo", state="open", limit=30)
    assert len(result) == 2
    assert result[0]["number"] == 10
