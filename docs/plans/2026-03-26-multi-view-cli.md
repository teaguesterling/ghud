# Multi-View CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand ghud from a single global dashboard into a multi-view CLI with issue, PR, and repo-specific views, powered by Typer.

**Architecture:** Replace argparse with Typer for CLI dispatch. Add repo context detection from git remotes. New rendering modules (`render_issue.py`, `render_pr.py`, `render_repo.py`) handle entity-specific Rich output. New API functions in `github.py` fetch issue/PR detail and PR lists. Pager wraps output by default.

**Tech Stack:** Python 3.10+, Typer, Rich, gh CLI (subprocess)

**Spec:** `docs/specs/2026-03-26-multi-view-cli-design.md`

---

### Task 1: Add Typer Dependency

**Files:**
- Modify: `pyproject.toml:27-31`

- [ ] **Step 1: Add typer to dependencies**

In `pyproject.toml`, add `typer>=0.9` to the dependencies list:

```toml
dependencies = [
    "rich>=13.0",
    "ruamel.yaml>=0.18",
    "fastmcp>=2.0",
    "typer>=0.9",
]
```

- [ ] **Step 2: Install updated dependencies**

Run: `pip install -e ".[dev]"`
Expected: Typer installs successfully alongside existing deps.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add typer dependency"
```

---

### Task 2: Repo Context Detection

**Files:**
- Create: `src/ghud/repo_context.py`
- Create: `tests/test_repo_context.py`

- [ ] **Step 1: Write failing tests for repo context detection**

```python
# tests/test_repo_context.py
import subprocess
import pytest
from ghud.repo_context import resolve_repo


def _mock_run(stdout_data, returncode=0):
    def mock(cmd, **kwargs):
        result = subprocess.CompletedProcess(cmd, returncode)
        result.stdout = stdout_data
        result.stderr = ""
        return result
    return mock


def test_resolve_repo_from_explicit_flag():
    """--repo flag takes priority over git detection."""
    assert resolve_repo(repo_flag="owner/myrepo") == "owner/myrepo"


def test_resolve_repo_from_explicit_flag_all():
    """--repo all returns None (meaning cross-repo)."""
    assert resolve_repo(repo_flag="all") is None


def test_resolve_repo_from_git_remote_https(monkeypatch):
    """Detects repo from HTTPS git remote."""
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("https://github.com/owner/myrepo.git\n"),
    )
    assert resolve_repo() == "owner/myrepo"


def test_resolve_repo_from_git_remote_ssh(monkeypatch):
    """Detects repo from SSH git remote."""
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("git@github.com:owner/myrepo.git\n"),
    )
    assert resolve_repo() == "owner/myrepo"


def test_resolve_repo_no_git_returns_none(monkeypatch):
    """Returns None when not in a git repo."""
    monkeypatch.setattr(
        subprocess, "run",
        _mock_run("", returncode=1),
    )
    assert resolve_repo() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_repo_context.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghud.repo_context'`

- [ ] **Step 3: Implement repo_context.py**

```python
# src/ghud/repo_context.py
"""Git remote detection and --repo flag resolution."""

import re
import subprocess


def _get_git_remote_url() -> str:
    """Get the origin remote URL from the current git directory."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _parse_repo_from_url(url: str) -> str | None:
    """Extract owner/repo from a GitHub remote URL."""
    # HTTPS: https://github.com/owner/repo.git
    # SSH: git@github.com:owner/repo.git
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
    if match:
        return match.group(1)
    return None


def resolve_repo(repo_flag: str | None = None) -> str | None:
    """Resolve the target repo.

    Returns owner/repo string, or None for cross-repo mode.
    - If repo_flag is provided and not "all", use it directly.
    - If repo_flag is "all", return None (cross-repo).
    - Otherwise, detect from git remote. Returns None if not in a git repo.
    """
    if repo_flag is not None:
        if repo_flag == "all":
            return None
        return repo_flag

    url = _get_git_remote_url()
    if not url:
        return None
    return _parse_repo_from_url(url)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_repo_context.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ghud/repo_context.py tests/test_repo_context.py
git commit -m "feat: add repo context detection from git remote"
```

---

### Task 3: Rewrite CLI with Typer

**Files:**
- Modify: `src/ghud/cli.py`
- Rewrite: `tests/test_cli.py`

This task replaces the argparse CLI with Typer. The `overview` command preserves existing dashboard behavior. `discover` and `serve` are re-wired. `issue`, `pr`, and `repo` subcommands are registered as stubs that print "not implemented yet" — they get real implementations in later tasks.

- [ ] **Step 1: Write failing tests for Typer CLI**

```python
# tests/test_cli.py
"""Tests for Typer CLI argument parsing and dispatch."""

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from ghud.cli import app

runner = CliRunner()


def test_overview_is_default():
    """Running ghud with no args invokes the overview (dashboard)."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        mock_dash.assert_called_once()


def test_overview_explicit():
    """ghud overview invokes the dashboard."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, ["overview"])
        assert result.exit_code == 0
        mock_dash.assert_called_once()


def test_overview_all_flag():
    """ghud overview --all passes show_all=True."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, ["overview", "--all"])
        assert result.exit_code == 0
        mock_dash.assert_called_once()
        call_kwargs = mock_dash.call_args
        assert call_kwargs[1]["show_all"] is True or call_kwargs[0][0] is True


def test_overview_days_flag():
    """ghud overview --days 14 passes days=14."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, ["overview", "--days", "14"])
        assert result.exit_code == 0
        mock_dash.assert_called_once()


def test_discover_subcommand():
    """ghud discover invokes run_discover."""
    with patch("ghud.cli.run_discover_cmd") as mock_disc:
        result = runner.invoke(app, ["discover"])
        assert result.exit_code == 0
        mock_disc.assert_called_once()


def test_discover_dry_run():
    """ghud discover --dry-run passes dry_run=True."""
    with patch("ghud.cli.run_discover_cmd") as mock_disc:
        result = runner.invoke(app, ["discover", "--dry-run"])
        assert result.exit_code == 0
        mock_disc.assert_called_once()


def test_serve_subcommand():
    """ghud serve invokes the MCP server."""
    with patch("ghud.cli.run_serve") as mock_serve:
        result = runner.invoke(app, ["serve"])
        assert result.exit_code == 0
        mock_serve.assert_called_once()


def test_issue_stub():
    """ghud issue subcommand is registered."""
    with patch("ghud.cli.run_issue_list") as mock_list:
        result = runner.invoke(app, ["issue"])
        assert result.exit_code == 0


def test_pr_stub():
    """ghud pr subcommand is registered."""
    with patch("ghud.cli.run_pr_list") as mock_list:
        result = runner.invoke(app, ["pr"])
        assert result.exit_code == 0


def test_repo_stub():
    """ghud repo subcommand is registered."""
    with patch("ghud.cli.run_repo_dashboard") as mock_repo:
        result = runner.invoke(app, ["repo"])
        assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `ImportError` because `app` doesn't exist yet in cli.py.

- [ ] **Step 3: Rewrite cli.py with Typer**

```python
# src/ghud/cli.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: All 10 tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

Run: `pytest -v`
Expected: All existing tests still pass (dashboard, data, github, config, discover, mcp tests are unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/ghud/cli.py tests/test_cli.py
git commit -m "feat: rewrite CLI with Typer, add subcommand stubs"
```

---

### Task 4: Pager Utility

**Files:**
- Create: `src/ghud/pager.py`
- Create: `tests/test_pager.py`

- [ ] **Step 1: Write failing tests for pager**

```python
# tests/test_pager.py
"""Tests for pager utility."""

from io import StringIO
from unittest.mock import patch
from rich.console import Console
from ghud.pager import render_with_pager


def test_render_with_pager_disabled():
    """When no_pager=True, renders directly without pager."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80)

    def render_fn(c: Console):
        c.print("Hello, world!")

    render_with_pager(render_fn, console=console, no_pager=True)
    output.seek(0)
    assert "Hello, world!" in output.read()


def test_render_with_pager_enabled():
    """When no_pager=False, wraps in console.pager()."""
    output = StringIO()
    console = Console(file=output, force_terminal=True, width=80)

    pager_entered = False

    original_pager = console.pager

    def tracking_pager(**kwargs):
        nonlocal pager_entered
        pager_entered = True
        return original_pager(**kwargs)

    console.pager = tracking_pager

    def render_fn(c: Console):
        c.print("Paged content")

    render_with_pager(render_fn, console=console, no_pager=False)
    assert pager_entered
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_pager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghud.pager'`

- [ ] **Step 3: Implement pager.py**

```python
# src/ghud/pager.py
"""Pager utility for Rich console output."""

from typing import Callable, Optional
from rich.console import Console


def render_with_pager(
    render_fn: Callable[[Console], None],
    console: Optional[Console] = None,
    no_pager: bool = False,
) -> None:
    """Render content, optionally wrapping in a pager.

    Args:
        render_fn: Function that takes a Console and prints to it.
        console: Rich Console instance. Created if not provided.
        no_pager: If True, render directly without pager.
    """
    if console is None:
        console = Console()

    if no_pager:
        render_fn(console)
    else:
        with console.pager(styles=True):
            render_fn(console)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_pager.py -v`
Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ghud/pager.py tests/test_pager.py
git commit -m "feat: add pager utility for Rich console output"
```

---

### Task 5: Issue Detail API

**Files:**
- Modify: `src/ghud/github.py`
- Modify: `tests/test_github.py`

- [ ] **Step 1: Write failing tests for get_issue_detail**

Add to the bottom of `tests/test_github.py`:

```python
from ghud.github import get_issue_detail


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_github.py::test_get_issue_detail tests/test_github.py::test_get_issue_detail_not_found -v`
Expected: FAIL — `ImportError: cannot import name 'get_issue_detail'`

- [ ] **Step 3: Implement get_issue_detail in github.py**

Add to the end of `src/ghud/github.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_github.py -v`
Expected: All tests PASS (existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/ghud/github.py tests/test_github.py
git commit -m "feat: add get_issue_detail API function"
```

---

### Task 6: PR Detail and PR List APIs

**Files:**
- Modify: `src/ghud/github.py`
- Modify: `tests/test_github.py`

- [ ] **Step 1: Write failing tests for PR APIs**

Add to the bottom of `tests/test_github.py`:

```python
from ghud.github import get_pr_detail, get_prs_for_repo


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_github.py::test_get_pr_detail tests/test_github.py::test_get_pr_detail_not_found tests/test_github.py::test_get_prs_for_repo -v`
Expected: FAIL — `ImportError: cannot import name 'get_pr_detail'`

- [ ] **Step 3: Implement PR APIs in github.py**

Add to the end of `src/ghud/github.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_github.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ghud/github.py tests/test_github.py
git commit -m "feat: add PR detail and PR list API functions"
```

---

### Task 7: Issue List Rendering

**Files:**
- Create: `src/ghud/render_issue.py`
- Create: `tests/test_render_issue.py`
- Modify: `src/ghud/cli.py`

- [ ] **Step 1: Write failing tests for issue list rendering**

```python
# tests/test_render_issue.py
"""Tests for issue rendering."""

from io import StringIO
from rich.console import Console
from ghud.render_issue import render_issue_list


def _make_console(width=120):
    return Console(file=StringIO(), width=width, force_terminal=True)


def _get_output(console):
    console.file.seek(0)
    return console.file.read()


def test_render_issue_list_single_repo():
    console = _make_console()
    issues = [
        {"number": 1, "title": "Bug report", "author": {"login": "alice"},
         "createdAt": "2026-03-20T00:00:00Z", "labels": [{"name": "bug"}]},
        {"number": 2, "title": "Feature request", "author": {"login": "bob"},
         "createdAt": "2026-03-19T00:00:00Z", "labels": []},
    ]
    render_issue_list(issues, repo="org/repo", console=console)
    output = _get_output(console)
    assert "Bug report" in output
    assert "Feature request" in output
    assert "alice" in output
    assert "bug" in output


def test_render_issue_list_cross_repo():
    console = _make_console()
    issues = [
        {"number": 1, "title": "Bug", "author": {"login": "alice"},
         "createdAt": "2026-03-20T00:00:00Z", "labels": [],
         "repo": "org/repo-a"},
        {"number": 5, "title": "Feature", "author": {"login": "bob"},
         "createdAt": "2026-03-19T00:00:00Z", "labels": [],
         "repo": "org/repo-b"},
    ]
    render_issue_list(issues, repo=None, console=console)
    output = _get_output(console)
    assert "Bug" in output
    assert "repo-a" in output
    assert "repo-b" in output


def test_render_issue_list_empty():
    console = _make_console()
    render_issue_list([], repo="org/repo", console=console)
    output = _get_output(console)
    assert "No issues" in output.lower() or "no open issues" in output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_issue.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghud.render_issue'`

- [ ] **Step 3: Implement render_issue_list**

```python
# src/ghud/render_issue.py
"""Issue rendering — list and detail views."""

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _days_ago(iso_date: str) -> int:
    """Calculate days between an ISO date string and now."""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, AttributeError):
        return 0


def _short_repo(full_name: str) -> str:
    """Shorten repo name: 'owner/repo' -> 'repo'."""
    parts = full_name.split("/")
    return parts[1] if len(parts) == 2 else full_name


def render_issue_list(
    issues: list[dict],
    repo: str | None = None,
    console: Optional[Console] = None,
) -> None:
    """Render a table of issues.

    Args:
        issues: List of issue dicts.
        repo: If set, single-repo mode (no repo column). If None, cross-repo mode.
        console: Rich Console. Created if not provided.
    """
    if console is None:
        console = Console()

    if not issues:
        console.print("[dim]No open issues found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("#", style="dim", width=6)
    if repo is None:
        table.add_column("Repo", style="cyan", width=25)
    table.add_column("Title")
    table.add_column("Author", width=15)
    table.add_column("Labels", width=20)
    table.add_column("Age", justify="right", width=8)

    for issue in issues:
        number = str(issue.get("number", ""))
        title = issue.get("title", "")
        author = issue.get("author", {}).get("login", "")
        labels = ", ".join(l["name"] for l in issue.get("labels", []))
        days = _days_ago(issue.get("createdAt", ""))
        age = f"{days}d"

        row = [number]
        if repo is None:
            issue_repo = issue.get("repo", "")
            row.append(_short_repo(issue_repo))
        row.extend([title, author, labels, age])
        table.add_row(*row)

    title_text = f"Issues — {repo}" if repo else "Issues (all repos)"
    panel = Panel(table, title=f"[bold]{title_text}[/bold]", border_style="blue")
    console.print(panel)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render_issue.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Wire issue list into CLI**

In `src/ghud/cli.py`, replace the `run_issue_list` placeholder:

```python
def run_issue_list(
    repo: str | None = None,
    state: str = "open",
    limit: int = 30,
    no_pager: bool = False,
) -> None:
    """Fetch and render the issue list."""
    from ghud.render_issue import render_issue_list
    from ghud.pager import render_with_pager

    if repo is not None:
        from ghud.github import get_issues_for_repo
        issues = get_issues_for_repo(repo)
        if state != "open":
            # get_issues_for_repo defaults to open; for other states, re-fetch
            from ghud.github import _run_gh_json
            issues = _run_gh_json([
                "issue", "list", "--repo", repo,
                "--state", state, "--limit", str(limit),
                "--json", "number,title,author,createdAt,url,labels",
            ])
    else:
        from ghud.config import find_yaml_path, load_repos_from_yaml
        from ghud.github import get_issues_for_repos_batch, get_username
        yaml_path = find_yaml_path()
        if not yaml_path:
            typer.echo("Error: Could not find projects.yaml", err=True)
            raise typer.Exit(1)
        repos = load_repos_from_yaml(yaml_path)
        username = get_username()
        issues = get_issues_for_repos_batch(repos, exclude_author=username)
        issues.sort(key=lambda x: x.get("createdAt", ""), reverse=True)

    issues = issues[:limit]

    def _render(console):
        render_issue_list(issues, repo=repo, console=console)

    render_with_pager(_render, no_pager=no_pager)
```

- [ ] **Step 6: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ghud/render_issue.py tests/test_render_issue.py src/ghud/cli.py
git commit -m "feat: add issue list view with Rich rendering"
```

---

### Task 8: Issue Detail Rendering

**Files:**
- Modify: `src/ghud/render_issue.py`
- Modify: `tests/test_render_issue.py`
- Modify: `src/ghud/cli.py`

- [ ] **Step 1: Write failing tests for issue detail rendering**

Add to `tests/test_render_issue.py`:

```python
from ghud.render_issue import render_issue_detail


def test_render_issue_detail_standard():
    """Standard detail: header + body + last N comments."""
    console = _make_console()
    issue = {
        "number": 42,
        "title": "Fix the thing",
        "state": "open",
        "body": "## Description\nThis needs fixing.",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "url": "https://github.com/org/repo/issues/42",
        "labels": [{"name": "bug"}, {"name": "priority-high"}],
        "assignees": [{"login": "bob"}],
        "milestone": {"title": "v2.0"},
        "comments": [
            {"author": {"login": "carol"}, "body": "I can reproduce.",
             "createdAt": "2026-03-21T00:00:00Z"},
            {"author": {"login": "dave"}, "body": "Looking into it.",
             "createdAt": "2026-03-22T00:00:00Z"},
            {"author": {"login": "eve"}, "body": "Fixed in #43.",
             "createdAt": "2026-03-23T00:00:00Z"},
        ],
    }
    render_issue_detail(issue, repo="org/repo", detail="standard", max_comments=3, console=console)
    output = _get_output(console)
    assert "Fix the thing" in output
    assert "alice" in output
    assert "bug" in output
    assert "v2.0" in output
    assert "Description" in output
    assert "Fixed in #43" in output


def test_render_issue_detail_brief():
    """Brief detail: header only, no body, comment count only."""
    console = _make_console()
    issue = {
        "number": 42,
        "title": "Fix the thing",
        "state": "open",
        "body": "Long body text that should not appear",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "milestone": None,
        "comments": [
            {"author": {"login": "carol"}, "body": "Comment 1",
             "createdAt": "2026-03-21T00:00:00Z"},
        ],
    }
    render_issue_detail(issue, repo="org/repo", detail="brief", max_comments=3, console=console)
    output = _get_output(console)
    assert "Fix the thing" in output
    assert "Long body text" not in output
    assert "Comment 1" not in output


def test_render_issue_detail_summary():
    """Summary detail: header, comment headers (no body text in comments)."""
    console = _make_console()
    issue = {
        "number": 42,
        "title": "Fix the thing",
        "state": "open",
        "body": "Body should not appear",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "milestone": None,
        "comments": [
            {"author": {"login": "carol"}, "body": "Detailed comment body",
             "createdAt": "2026-03-21T00:00:00Z"},
        ],
    }
    render_issue_detail(issue, repo="org/repo", detail="summary", max_comments=3, console=console)
    output = _get_output(console)
    assert "Fix the thing" in output
    assert "Body should not appear" not in output
    assert "carol" in output
    assert "Detailed comment body" not in output


def test_render_issue_detail_truncates_comments():
    """Only shows the last max_comments comments."""
    console = _make_console()
    issue = {
        "number": 42,
        "title": "Test",
        "state": "open",
        "body": "Body",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "milestone": None,
        "comments": [
            {"author": {"login": f"user{i}"}, "body": f"Comment {i}",
             "createdAt": f"2026-03-{20+i}T00:00:00Z"}
            for i in range(10)
        ],
    }
    render_issue_detail(issue, repo="org/repo", detail="standard", max_comments=2, console=console)
    output = _get_output(console)
    assert "Comment 8" in output
    assert "Comment 9" in output
    assert "Comment 0" not in output
    assert "showing 2 of 10" in output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_issue.py::test_render_issue_detail_standard -v`
Expected: FAIL — `ImportError: cannot import name 'render_issue_detail'`

- [ ] **Step 3: Implement render_issue_detail**

Add to `src/ghud/render_issue.py`:

```python
from rich.markdown import Markdown
from rich.rule import Rule


def render_issue_detail(
    issue: dict,
    repo: str,
    detail: str = "standard",
    max_comments: int = 3,
    console: Optional[Console] = None,
) -> None:
    """Render a detailed issue view.

    Args:
        issue: Issue dict from get_issue_detail.
        repo: Repository identifier (owner/repo).
        detail: One of 'brief', 'summary', 'standard', 'full'.
        max_comments: Max comments to show (ignored for 'full' which shows all).
        console: Rich Console.
    """
    if console is None:
        console = Console()

    number = issue.get("number", "")
    title = issue.get("title", "")
    state = issue.get("state", "unknown")
    author = issue.get("author", {}).get("login", "unknown")
    created = issue.get("createdAt", "")
    days = _days_ago(created)
    labels = issue.get("labels", [])
    assignees = issue.get("assignees", [])
    milestone = issue.get("milestone")
    body = issue.get("body", "")
    comments = issue.get("comments", [])

    # Header
    state_style = "green" if state.lower() == "open" else "red"
    header_lines = []
    header_lines.append(f"[bold]{title}[/bold]")
    meta_parts = [
        f"[{state_style}]{state}[/{state_style}]",
        f"@{author}",
        f"{days}d ago",
        f"{len(comments)} comment{'s' if len(comments) != 1 else ''}",
    ]
    header_lines.append(" · ".join(meta_parts))

    if labels:
        label_str = ", ".join(l["name"] for l in labels)
        header_lines.append(f"Labels: {label_str}")
    if milestone:
        header_lines.append(f"Milestone: {milestone.get('title', '')}")
    if assignees:
        assignee_str = ", ".join(f"@{a['login']}" for a in assignees)
        header_lines.append(f"Assignees: {assignee_str}")

    header_text = "\n".join(header_lines)
    console.print(Panel(
        header_text,
        title=f"[bold]Issue #{number} · {repo}[/bold]",
        border_style="blue",
    ))

    # Body (standard and full only)
    if detail in ("standard", "full") and body:
        console.print(Panel(
            Markdown(body),
            title="[bold]Description[/bold]",
            border_style="dim",
        ))

    # Comments
    if detail == "brief":
        # Brief: just the count, already in header
        return

    if detail == "full":
        display_comments = comments
    else:
        display_comments = comments[-max_comments:] if max_comments else comments

    if not comments:
        return

    total = len(comments)
    showing = len(display_comments)
    if showing < total:
        comment_title = f"Comments (showing {showing} of {total})"
    else:
        comment_title = f"Comments ({total})"

    comment_parts = []
    for c in display_comments:
        c_author = c.get("author", {}).get("login", "unknown")
        c_date = c.get("createdAt", "")
        c_days = _days_ago(c_date)
        c_body = c.get("body", "")

        if detail == "summary":
            comment_parts.append(f"[bold]@{c_author}[/bold] · {c_days}d ago")
        else:
            comment_parts.append(f"[bold]@{c_author}[/bold] · {c_days}d ago\n{c_body}")

    console.print(Panel(
        "\n\n".join(comment_parts),
        title=f"[bold]{comment_title}[/bold]",
        border_style="dim",
    ))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render_issue.py -v`
Expected: All 7 tests PASS (3 list + 4 detail).

- [ ] **Step 5: Wire issue detail into CLI**

In `src/ghud/cli.py`, replace the `run_issue_detail` placeholder:

```python
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
```

- [ ] **Step 6: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ghud/render_issue.py tests/test_render_issue.py src/ghud/cli.py
git commit -m "feat: add issue detail view with detail levels and comment truncation"
```

---

### Task 9: PR List Rendering

**Files:**
- Create: `src/ghud/render_pr.py`
- Create: `tests/test_render_pr.py`
- Modify: `src/ghud/cli.py`

- [ ] **Step 1: Write failing tests for PR list rendering**

```python
# tests/test_render_pr.py
"""Tests for PR rendering."""

from io import StringIO
from rich.console import Console
from ghud.render_pr import render_pr_list


def _make_console(width=120):
    return Console(file=StringIO(), width=width, force_terminal=True)


def _get_output(console):
    console.file.seek(0)
    return console.file.read()


def test_render_pr_list_single_repo():
    console = _make_console()
    prs = [
        {"number": 10, "title": "Add feature", "author": {"login": "alice"},
         "createdAt": "2026-03-20T00:00:00Z",
         "statusCheckRollup": [
             {"status": "COMPLETED", "conclusion": "SUCCESS"},
         ],
         "reviewDecision": "APPROVED"},
        {"number": 11, "title": "Fix bug", "author": {"login": "bob"},
         "createdAt": "2026-03-21T00:00:00Z",
         "statusCheckRollup": [
             {"status": "COMPLETED", "conclusion": "FAILURE"},
         ],
         "reviewDecision": ""},
    ]
    render_pr_list(prs, repo="org/repo", console=console)
    output = _get_output(console)
    assert "Add feature" in output
    assert "Fix bug" in output
    assert "alice" in output


def test_render_pr_list_empty():
    console = _make_console()
    render_pr_list([], repo="org/repo", console=console)
    output = _get_output(console)
    assert "no" in output.lower()


def test_render_pr_list_check_status_indicators():
    """Check status should show visual indicators."""
    console = _make_console()
    prs = [
        {"number": 1, "title": "All passing", "author": {"login": "a"},
         "createdAt": "2026-03-20T00:00:00Z",
         "statusCheckRollup": [
             {"status": "COMPLETED", "conclusion": "SUCCESS"},
         ],
         "reviewDecision": "APPROVED"},
    ]
    render_pr_list(prs, repo="org/repo", console=console)
    output = _get_output(console)
    # Should contain a check indicator (✓ or similar)
    assert "✓" in output or "APPROVED" in output or "passing" in output.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_pr.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghud.render_pr'`

- [ ] **Step 3: Implement render_pr_list**

```python
# src/ghud/render_pr.py
"""PR rendering — list and detail views."""

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _days_ago(iso_date: str) -> int:
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, AttributeError):
        return 0


def _short_repo(full_name: str) -> str:
    parts = full_name.split("/")
    return parts[1] if len(parts) == 2 else full_name


def _check_status_indicator(checks: list[dict]) -> Text:
    """Return a single-character check status indicator.

    ✓ = all passing, ✗ = any failing, ● = pending, — = no checks.
    """
    if not checks:
        return Text("—", style="dim")

    has_failure = any(
        c.get("conclusion") in ("FAILURE", "CANCELLED", "TIMED_OUT")
        for c in checks
    )
    if has_failure:
        return Text("✗", style="bold red")

    has_pending = any(
        c.get("status") != "COMPLETED"
        for c in checks
    )
    if has_pending:
        return Text("●", style="yellow")

    return Text("✓", style="green")


def _review_indicator(decision: str) -> str:
    """Short review status string."""
    mapping = {
        "APPROVED": "✓",
        "CHANGES_REQUESTED": "✗",
        "REVIEW_REQUIRED": "●",
    }
    return mapping.get(decision, "")


def render_pr_list(
    prs: list[dict],
    repo: str | None = None,
    console: Optional[Console] = None,
) -> None:
    """Render a table of PRs.

    Args:
        prs: List of PR dicts.
        repo: If set, single-repo mode. If None, cross-repo mode.
        console: Rich Console.
    """
    if console is None:
        console = Console()

    if not prs:
        console.print("[dim]No open pull requests found.[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("#", style="dim", width=6)
    if repo is None:
        table.add_column("Repo", style="cyan", width=25)
    table.add_column("Title")
    table.add_column("Author", width=15)
    table.add_column("Status", width=8, justify="center")
    table.add_column("Age", justify="right", width=8)

    for pr in prs:
        number = str(pr.get("number", ""))
        title = pr.get("title", "")
        author = pr.get("author", {}).get("login", "")
        checks = pr.get("statusCheckRollup", []) or []
        review = pr.get("reviewDecision", "") or ""
        days = _days_ago(pr.get("createdAt", ""))

        check_ind = _check_status_indicator(checks)
        review_ind = _review_indicator(review)
        status = Text()
        status.append_text(check_ind)
        if review_ind:
            status.append(" ")
            status.append(review_ind)

        row = [number]
        if repo is None:
            pr_repo = pr.get("repository", {}).get("nameWithOwner", "")
            row.append(_short_repo(pr_repo))
        row.extend([title, author, status, f"{days}d"])
        table.add_row(*row)

    title_text = f"Pull Requests — {repo}" if repo else "Pull Requests (all repos)"
    panel = Panel(table, title=f"[bold]{title_text}[/bold]", border_style="yellow")
    console.print(panel)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render_pr.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Wire PR list into CLI**

In `src/ghud/cli.py`, replace the `run_pr_list` placeholder:

```python
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
```

- [ ] **Step 6: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ghud/render_pr.py tests/test_render_pr.py src/ghud/cli.py
git commit -m "feat: add PR list view with check status indicators"
```

---

### Task 10: PR Detail Rendering

**Files:**
- Modify: `src/ghud/render_pr.py`
- Modify: `tests/test_render_pr.py`
- Modify: `src/ghud/cli.py`

- [ ] **Step 1: Write failing tests for PR detail rendering**

Add to `tests/test_render_pr.py`:

```python
from ghud.render_pr import render_pr_detail


def test_render_pr_detail_standard():
    """Standard: header with check indicator + body + last N comments."""
    console = _make_console()
    pr = {
        "number": 15,
        "title": "Add feature X",
        "state": "OPEN",
        "body": "## Changes\nAdds feature X.",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [{"name": "enhancement"}],
        "assignees": [{"login": "bob"}],
        "reviewDecision": "APPROVED",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"name": "ci/build", "status": "COMPLETED", "conclusion": "SUCCESS"},
        ],
        "comments": [
            {"author": {"login": "carol"}, "body": "LGTM!",
             "createdAt": "2026-03-21T00:00:00Z"},
        ],
        "reviews": [
            {"author": {"login": "carol"}, "state": "APPROVED",
             "body": "", "submittedAt": "2026-03-21T00:00:00Z"},
        ],
    }
    render_pr_detail(pr, repo="org/repo", detail="standard", max_comments=3, console=console)
    output = _get_output(console)
    assert "Add feature X" in output
    assert "alice" in output
    assert "Changes" in output
    assert "LGTM" in output
    # Should have check status indicator
    assert "✓" in output


def test_render_pr_detail_full_expands_checks():
    """Full detail: shows individual check names."""
    console = _make_console()
    pr = {
        "number": 15,
        "title": "Add feature X",
        "state": "OPEN",
        "body": "Body text",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "reviewDecision": "",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [
            {"name": "ci/build", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "ci/lint", "status": "COMPLETED", "conclusion": "FAILURE"},
        ],
        "comments": [],
        "reviews": [],
    }
    render_pr_detail(pr, repo="org/repo", detail="full", max_comments=3, console=console)
    output = _get_output(console)
    assert "ci/build" in output
    assert "ci/lint" in output


def test_render_pr_detail_brief():
    """Brief: header only, no body or comments."""
    console = _make_console()
    pr = {
        "number": 15,
        "title": "Add feature X",
        "state": "OPEN",
        "body": "Should not appear",
        "author": {"login": "alice"},
        "createdAt": "2026-03-20T00:00:00Z",
        "labels": [],
        "assignees": [],
        "reviewDecision": "",
        "mergeable": "MERGEABLE",
        "statusCheckRollup": [],
        "comments": [
            {"author": {"login": "carol"}, "body": "Hidden comment",
             "createdAt": "2026-03-21T00:00:00Z"},
        ],
        "reviews": [],
    }
    render_pr_detail(pr, repo="org/repo", detail="brief", max_comments=3, console=console)
    output = _get_output(console)
    assert "Add feature X" in output
    assert "Should not appear" not in output
    assert "Hidden comment" not in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_pr.py::test_render_pr_detail_standard -v`
Expected: FAIL — `ImportError: cannot import name 'render_pr_detail'`

- [ ] **Step 3: Implement render_pr_detail**

Add to `src/ghud/render_pr.py`:

```python
from rich.markdown import Markdown


def render_pr_detail(
    pr: dict,
    repo: str,
    detail: str = "standard",
    max_comments: int = 3,
    console: Optional[Console] = None,
) -> None:
    """Render a detailed PR view.

    Args:
        pr: PR dict from get_pr_detail.
        repo: Repository identifier.
        detail: One of 'brief', 'summary', 'standard', 'full'.
        max_comments: Max comments to show.
        console: Rich Console.
    """
    if console is None:
        console = Console()

    number = pr.get("number", "")
    title = pr.get("title", "")
    state = pr.get("state", "OPEN")
    author = pr.get("author", {}).get("login", "unknown")
    created = pr.get("createdAt", "")
    days = _days_ago(created)
    labels = pr.get("labels", [])
    assignees = pr.get("assignees", [])
    body = pr.get("body", "")
    comments = pr.get("comments", [])
    reviews = pr.get("reviews", [])
    checks = pr.get("statusCheckRollup", []) or []
    review_decision = pr.get("reviewDecision", "") or ""
    mergeable = pr.get("mergeable", "")

    # State styling
    state_lower = state.lower()
    if state_lower == "merged":
        state_style = "magenta"
    elif state_lower == "closed":
        state_style = "red"
    else:
        state_style = "green"

    # Header
    header_lines = []
    header_lines.append(f"[bold]{title}[/bold]")

    check_ind = _check_status_indicator(checks)
    meta_parts = [
        f"[{state_style}]{state}[/{state_style}]",
        f"@{author}",
        f"{days}d ago",
        f"{len(comments)} comment{'s' if len(comments) != 1 else ''}",
    ]
    header_lines.append(" · ".join(meta_parts))

    # Review + check status line
    status_parts = []
    status_parts.append(f"Checks: {check_ind.plain}")
    if review_decision:
        status_parts.append(f"Review: {review_decision}")
    if mergeable:
        status_parts.append(f"Mergeable: {mergeable}")
    header_lines.append("  ".join(status_parts))

    if labels:
        header_lines.append(f"Labels: {', '.join(l['name'] for l in labels)}")
    if assignees:
        header_lines.append(f"Assignees: {', '.join(f'@{a[\"login\"]}' for a in assignees)}")

    console.print(Panel(
        "\n".join(header_lines),
        title=f"[bold]PR #{number} · {repo}[/bold]",
        border_style="yellow",
    ))

    # Expanded checks (full only)
    if detail == "full" and checks:
        check_lines = []
        for c in checks:
            name = c.get("name", "unknown")
            conclusion = c.get("conclusion", c.get("status", "unknown"))
            if conclusion == "SUCCESS":
                check_lines.append(f"  [green]✓[/green] {name}")
            elif conclusion in ("FAILURE", "CANCELLED", "TIMED_OUT"):
                check_lines.append(f"  [red]✗[/red] {name}")
            else:
                check_lines.append(f"  [yellow]●[/yellow] {name}")
        console.print(Panel(
            "\n".join(check_lines),
            title="[bold]Checks[/bold]",
            border_style="dim",
        ))

    # Body (standard and full only)
    if detail in ("standard", "full") and body:
        console.print(Panel(
            Markdown(body),
            title="[bold]Description[/bold]",
            border_style="dim",
        ))

    # Comments
    if detail == "brief":
        return

    if detail == "full":
        display_comments = comments
    else:
        display_comments = comments[-max_comments:] if max_comments else comments

    if not comments:
        return

    total = len(comments)
    showing = len(display_comments)
    if showing < total:
        comment_title = f"Comments (showing {showing} of {total})"
    else:
        comment_title = f"Comments ({total})"

    comment_parts = []
    for c in display_comments:
        c_author = c.get("author", {}).get("login", "unknown")
        c_date = c.get("createdAt", "")
        c_days = _days_ago(c_date)
        c_body = c.get("body", "")

        if detail == "summary":
            comment_parts.append(f"[bold]@{c_author}[/bold] · {c_days}d ago")
        else:
            comment_parts.append(f"[bold]@{c_author}[/bold] · {c_days}d ago\n{c_body}")

    console.print(Panel(
        "\n\n".join(comment_parts),
        title=f"[bold]{comment_title}[/bold]",
        border_style="dim",
    ))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render_pr.py -v`
Expected: All 6 tests PASS (3 list + 3 detail).

- [ ] **Step 5: Wire PR detail into CLI**

In `src/ghud/cli.py`, replace the `run_pr_detail` placeholder:

```python
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
```

- [ ] **Step 6: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ghud/render_pr.py tests/test_render_pr.py src/ghud/cli.py
git commit -m "feat: add PR detail view with checks, reviews, and comment truncation"
```

---

### Task 11: Repo Dashboard

**Files:**
- Create: `src/ghud/render_repo.py`
- Create: `tests/test_render_repo.py`
- Modify: `src/ghud/cli.py`

- [ ] **Step 1: Write failing tests for repo dashboard**

```python
# tests/test_render_repo.py
"""Tests for repo dashboard rendering."""

from io import StringIO
from rich.console import Console
from ghud.render_repo import render_repo_dashboard


def _make_console(width=120):
    return Console(file=StringIO(), width=width, force_terminal=True)


def _get_output(console):
    console.file.seek(0)
    return console.file.read()


def test_render_repo_dashboard():
    console = _make_console()
    data = {
        "issues": [
            {"number": 1, "title": "Bug", "author": {"login": "alice"},
             "createdAt": "2026-03-20T00:00:00Z", "labels": [{"name": "bug"}]},
        ],
        "prs": [
            {"number": 10, "title": "Fix", "author": {"login": "bob"},
             "createdAt": "2026-03-21T00:00:00Z",
             "statusCheckRollup": [], "reviewDecision": ""},
        ],
    }
    render_repo_dashboard(data, repo="org/repo", console=console)
    output = _get_output(console)
    assert "Bug" in output
    assert "Fix" in output
    assert "org/repo" in output


def test_render_repo_dashboard_empty():
    console = _make_console()
    data = {"issues": [], "prs": []}
    render_repo_dashboard(data, repo="org/repo", console=console)
    output = _get_output(console)
    assert "no" in output.lower() or "org/repo" in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_render_repo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ghud.render_repo'`

- [ ] **Step 3: Implement render_repo_dashboard**

```python
# src/ghud/render_repo.py
"""Repo-level dashboard rendering."""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ghud.render_issue import render_issue_list
from ghud.render_pr import render_pr_list


def render_repo_dashboard(
    data: dict,
    repo: str,
    console: Optional[Console] = None,
) -> None:
    """Render a repo-level dashboard with issues and PRs summary.

    Args:
        data: Dict with 'issues' and 'prs' keys.
        repo: Repository identifier (owner/repo).
        console: Rich Console.
    """
    if console is None:
        console = Console()

    issues = data.get("issues", [])
    prs = data.get("prs", [])

    console.print(f"\n[bold]Repository Dashboard — {repo}[/bold]\n")

    if not issues and not prs:
        console.print("[dim]No open issues or pull requests.[/dim]")
        return

    if issues:
        render_issue_list(issues, repo=repo, console=console)
        console.print()

    if prs:
        render_pr_list(prs, repo=repo, console=console)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_render_repo.py -v`
Expected: All 2 tests PASS.

- [ ] **Step 5: Wire repo dashboard into CLI**

In `src/ghud/cli.py`, replace the `run_repo_dashboard` placeholder:

```python
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
```

- [ ] **Step 6: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ghud/render_repo.py tests/test_render_repo.py src/ghud/cli.py
git commit -m "feat: add repo-level dashboard view"
```

---

### Task 12: Subcommand Aliases

**Files:**
- Modify: `src/ghud/cli.py`
- Modify: `tests/test_cli.py`

Typer doesn't natively support aliases like `i` for `issue`. We use the `rich_click` approach of registering the same function under multiple names, or use Typer's `name` parameter with a custom Click group.

- [ ] **Step 1: Write failing tests for aliases**

Add to `tests/test_cli.py`:

```python
def test_issue_alias_i():
    """ghud i should work like ghud issue."""
    with patch("ghud.cli.run_issue_list") as mock_list:
        result = runner.invoke(app, ["i"])
        assert result.exit_code == 0


def test_pr_alias():
    """ghud pr should work."""
    with patch("ghud.cli.run_pr_list") as mock_list:
        result = runner.invoke(app, ["pr"])
        assert result.exit_code == 0


def test_repo_alias_r():
    """ghud r should work like ghud repo."""
    with patch("ghud.cli.run_repo_dashboard") as mock_repo:
        result = runner.invoke(app, ["r"])
        assert result.exit_code == 0


def test_overview_alias_o():
    """ghud o should work like ghud overview."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, ["o"])
        assert result.exit_code == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py::test_issue_alias_i tests/test_cli.py::test_repo_alias_r tests/test_cli.py::test_overview_alias_o -v`
Expected: FAIL — aliases not registered yet.

- [ ] **Step 3: Implement aliases using a custom Click group**

At the top of `src/ghud/cli.py`, add a custom group class that supports aliases, then use it as the Typer cls:

```python
import click


class AliasGroup(click.Group):
    """Click group that supports command aliases."""

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
```

Then update the app creation:

```python
app = typer.Typer(
    name="ghud",
    help="GitHub Heads-Up Display — terminal dashboard for your portfolio repos",
    invoke_without_command=True,
    cls=AliasGroup,
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: All tests PASS (original + 4 alias tests).

- [ ] **Step 5: Run full test suite**

Run: `pytest -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/ghud/cli.py tests/test_cli.py
git commit -m "feat: add subcommand aliases (i, o, r)"
```

---

### Task 13: Integration Smoke Test

**Files:**
- Create: `tests/test_integration.py`

A lightweight integration test that verifies the end-to-end flow (CLI → API mock → render) works for each subcommand.

- [ ] **Step 1: Write integration tests**

```python
# tests/test_integration.py
"""Integration smoke tests for CLI subcommands."""

import subprocess
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from ghud.cli import app

runner = CliRunner()


def _mock_subprocess_run(cmd, **kwargs):
    """Return plausible mock data based on the command."""
    import json
    result = subprocess.CompletedProcess(cmd, 0)
    result.stderr = ""

    cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd

    if "issue" in cmd_str and "view" in cmd_str:
        result.stdout = json.dumps({
            "number": 42, "title": "Test issue", "state": "open",
            "body": "Test body", "author": {"login": "tester"},
            "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
            "labels": [], "assignees": [], "milestone": None,
            "comments": [],
        })
    elif "issue" in cmd_str and "list" in cmd_str:
        result.stdout = json.dumps([
            {"number": 1, "title": "Issue A", "author": {"login": "a"},
             "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
             "labels": []},
        ])
    elif "pr" in cmd_str and "view" in cmd_str:
        result.stdout = json.dumps({
            "number": 15, "title": "Test PR", "state": "OPEN",
            "body": "PR body", "author": {"login": "tester"},
            "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
            "labels": [], "assignees": [], "reviewDecision": "",
            "mergeable": "MERGEABLE", "statusCheckRollup": [],
            "comments": [], "reviews": [],
        })
    elif "pr" in cmd_str and "list" in cmd_str:
        result.stdout = json.dumps([
            {"number": 10, "title": "PR A", "author": {"login": "a"},
             "createdAt": "2026-03-20T00:00:00Z", "url": "https://...",
             "state": "OPEN", "statusCheckRollup": [], "reviewDecision": ""},
        ])
    elif "remote" in cmd_str:
        result.stdout = "https://github.com/org/repo.git\n"
    else:
        result.stdout = "[]"

    return result


def test_issue_list_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["issue", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
        assert "Issue A" in result.output


def test_issue_detail_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["issue", "42", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
        assert "Test issue" in result.output


def test_pr_list_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["pr", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
        assert "PR A" in result.output


def test_pr_detail_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["pr", "15", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
        assert "Test PR" in result.output


def test_repo_dashboard_smoke():
    with patch("subprocess.run", side_effect=_mock_subprocess_run):
        result = runner.invoke(app, ["repo", "--repo", "org/repo", "--no-pager"])
        assert result.exit_code == 0
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`
Expected: All tests across all test files PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration smoke tests for all CLI subcommands"
```
