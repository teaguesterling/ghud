import json
import subprocess
import pytest
from ghud.github import (
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


def _mock_run(stdout_data, returncode=0):
    """Create a mock for subprocess.run that returns given stdout."""
    def mock(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, returncode)
        result.stdout = stdout_data if isinstance(stdout_data, str) else json.dumps(stdout_data)
        result.stderr = ""
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
    data = [
        {"title": "Merged PR", "repository": {"nameWithOwner": "org/repo"},
         "closedAt": "2026-03-22T00:00:00Z", "url": "https://..."},
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
    monkeypatch.setattr(subprocess, "run", _mock_run("", returncode=1))
    result = get_issue_detail("org/repo", 999)
    assert result == {}


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
    monkeypatch.setattr(subprocess, "run", _mock_run("", returncode=1))
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
