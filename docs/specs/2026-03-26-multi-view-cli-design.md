# Multi-View CLI Design

**Date:** 2026-03-26
**Status:** Draft

## Motivation

The `gh` CLI requires long, verbose field specifications and makes it hard to retrieve GitHub information quickly. ghud currently provides a single global dashboard. This design adds entity-specific views so that commands like `ghud i 42` produce a rich, formatted display of issue #42 without needing to remember `gh` field flags or open a browser.

## CLI Structure

### Framework

Migrate from argparse to Typer. Typer provides type-annotated argument definitions, automatic help generation, and is built on Click for escape-hatch flexibility.

**Dependency:** `typer>=0.9`

**Entry point:** `ghud.cli:main` (unchanged path, implementation changes to Typer app invocation).

### Subcommands

```
ghud                          # alias for ghud overview
ghud overview / ghud o        # global dashboard (existing behavior)
ghud repo / ghud r            # repo-level dashboard
ghud issue / ghud i           # issue list or detail
ghud pr                       # PR list or detail
ghud discover                 # existing discover command
ghud serve                    # existing MCP server
```

### Global Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--repo <owner/repo>` | Override repo context. `--repo all` for cross-repo. | Auto-detect from git remote |
| `--no-pager` | Disable pager | `false` |
| `--user <username>` | Specify GitHub user | Authenticated `gh` user |

### Subcommand Flags

| Flag | Available on | Default |
|------|-------------|---------|
| `--detail brief\|summary\|standard\|full` | `issue <N>`, `pr <N>` | `standard` |
| `--comments <N>` or `--comments all` | `issue <N>`, `pr <N>` | `3` |
| `--state open\|closed\|all` | `issue`, `pr` (list mode) | `open` |
| `--limit N` | `issue`, `pr` (list mode) | `30` |
| `--all` | `overview` | `false` |
| `--days N` | `overview` | `7` |

### Positional Arguments

`issue` and `pr` take an optional number:
- Present: detail view (e.g., `ghud i 42`)
- Absent: list view (e.g., `ghud i`)

### Repo Detection Logic

Shared utility in `repo_context.py`:

1. If `--repo` is provided, use it directly
2. Otherwise, parse the `origin` remote URL from the current git directory
3. If not in a git repo: behave as `--repo all` for list commands; error for detail commands that require a repo

## Detail Levels

The `--detail` flag controls both what gets fetched and what gets displayed:

| Level | Body | Comments | Timeline/Reviews | Check Status |
|-------|------|----------|-------------------|--------------|
| `brief` | No | Count only (e.g., "5 comments") | No | No |
| `summary` | No | All comments, header only (author + date, no body) | No | No |
| `standard` | Yes (rendered markdown) | Last N (full text) | No | Single indicator |
| `full` | Yes (rendered markdown) | All (full text) | Yes | Expanded per-check |

## Data Fetching

### New API Functions (`github.py`)

- **`get_repo_from_git_remote()`** — Parse `origin` remote URL to extract `owner/repo`
- **`get_issue_detail(repo, number)`** — Single issue with body, labels, assignees, milestone, comments via `gh issue view`
- **`get_pr_detail(repo, number)`** — Single PR with body, labels, assignees, reviews, check status, comments via `gh pr view`
- **`get_prs_for_repo(repo, state, limit)`** — PR list for a single repo
- **`get_prs_for_repos_batch(repos, state, limit)`** — Batch PR fetch across portfolio repos (same pattern as existing `get_issues_for_repos_batch`)

### Existing Functions (unchanged)

- `get_issues_for_repo()` — single-repo issue lists
- `get_issues_for_repos_batch()` — cross-repo issue lists
- `get_username()` — default user
- All existing dashboard data functions

## Rendering

### Issue Detail View (`ghud i 42`)

```
+-  Issue #42 . owner/repo ------------------------------------+
| Title of the issue                                           |
| open . @author . 3 days ago . 5 comments                    |
| Labels: bug, priority-high    Milestone: v2.0               |
| Assignees: @alice, @bob                                      |
+--------------------------------------------------------------+
| (rendered markdown body)                                     |
+- Comments (showing 3 of 12) --------------------------------+
| @carol . 2 days ago                                          |
|   comment body...                                            |
|                                                              |
| @dave . 1 day ago                                            |
|   comment body...                                            |
|                                                              |
| @eve . 3 hours ago                                           |
|   comment body...                                            |
+--------------------------------------------------------------+
```

### PR Detail View (`ghud pr 15`)

Same layout as issue detail, plus:
- Check status indicator in the header (standard: single char `✓`/`✗`/`●`/`—`; full: expanded list)
- Review status (approved, changes requested, pending)
- Merge state (open, merged, closed)

### List Views (`ghud i`, `ghud pr`)

Rich tables matching existing dashboard panel style:
- **Issue list columns:** `#`, `Title`, `Author`, `Labels`, `Age`
- **PR list columns:** `#`, `Title`, `Author`, `Status` (checks/reviews), `Age`

### Repo Dashboard (`ghud r`)

Composite view scoped to one repo: open issues summary + open PRs summary + recent activity, using panel layout similar to the overview.

### Pager

Wrap output in `console.pager()` by default when content exceeds terminal height. `--no-pager` disables.

### Markdown Body Rendering

Use Rich's built-in `Markdown` renderer for issue/PR bodies in the terminal.

## Module Organization

### New Files

| File | Purpose |
|------|---------|
| `src/ghud/render_issue.py` | Issue detail + list rendering (Rich) |
| `src/ghud/render_pr.py` | PR detail + list rendering (Rich) |
| `src/ghud/render_repo.py` | Repo-level dashboard rendering (Rich) |
| `src/ghud/repo_context.py` | Git remote detection + `--repo` resolution |

### Modified Files

| File | Changes |
|------|---------|
| `cli.py` | Rewrite from argparse to Typer, define all subcommands |
| `github.py` | Add new API functions for issue/PR detail, PR lists, git remote parsing |
| `pyproject.toml` | Add `typer>=0.9` dependency |

### Unchanged Files

| File | Reason |
|------|--------|
| `dashboard.py` | Overview rendering stays as-is |
| `data.py` | Dashboard data fetching stays as-is |
| `config.py` | No changes needed |
| `discover.py` | Logic unchanged, just re-wired through Typer |
| `mcp.py` | Out of scope for this round |

## Testing

Each new module gets its own test file following the existing pattern:
- Mock subprocess calls to `gh` CLI
- Test rendering output with Rich console capture
- Test repo context detection with mocked git state
- Test detail level filtering
- Test list view defaults and flag overrides

## Out of Scope

- MCP server tools for new views (future work)
- Markdown output renderers for new views (future work, for MCP integration)
