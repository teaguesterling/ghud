# ghud v0.2.0 — MCP Server + XDG Config

## Overview

Add an MCP server to ghud (via fastmcp, stdio transport) exposing dashboard data as tools for AI agents. Move config discovery to XDG-compliant paths.

## MCP Server

### File: `src/ghud/mcp.py`

Uses fastmcp to expose the following tools:

| Tool | Returns | Params | Description |
|------|---------|--------|-------------|
| `get_dashboard` | Markdown string | `show_all: bool = False`, `days: int = 7` | Full dashboard as markdown |
| `get_notifications` | JSON list | `important_only: bool = True` | Notifications with reason, repo, title |
| `get_open_prs` | JSON list | (none) | Open PRs with repo, title, createdAt, commentsCount (raw API fields) |
| `get_merged_prs` | JSON list | `days: int = 7` | Recently merged PRs |
| `get_issues_from_others` | JSON list | (none) | Issues on portfolio repos not authored by user |
| `get_portfolio_repos` | JSON list | (none) | Repos from projects.yaml |
| `discover_repos` | JSON list | (none) | Repos on GitHub not in projects.yaml |

### Entry Points

- CLI: `ghud serve` subcommand runs the MCP server (stdio)
- Script: `ghud-mcp = "ghud.mcp:main"` in pyproject.toml for direct MCP client config

### Transport

stdio by default (fastmcp handles this). HTTP/SSE can be added later by changing the transport parameter — no code changes needed.

### Dependency

`fastmcp>=2.0` added to project dependencies.

## XDG Config

### Path Resolution Order (in `config.py`)

1. `$XDG_CONFIG_HOME/ghud/projects.yaml` (defaults to `~/.config/ghud/projects.yaml`)
2. `~/Projects/pages/src/_data/projects.yaml` (legacy)
3. `/mnt/aux-data/teague/Projects/pages/src/_data/projects.yaml` (legacy)

First existing path wins. No automatic migration — user moves the file manually.

### Implementation

Update `DEFAULT_YAML_CANDIDATES` in `config.py` to prepend the XDG path. Use `os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))`.

## Data Layer Refactoring

### New File: `src/ghud/data.py`

Extract shared data-fetching logic from `cli.py` so both CLI and MCP can use it:

```python
def fetch_dashboard_data(repos, username, days=7):
    """Fetch all dashboard data concurrently. Returns data dict."""
    # ThreadPoolExecutor + GraphQL batch logic moves here from cli.py

def collect_other_activity(notifications, portfolio_repos):
    """Split notifications into portfolio vs other. Moves from cli.py."""
```

### Impact on `cli.py`

`run_dashboard()` becomes a thin wrapper: calls `fetch_dashboard_data()` then `render_dashboard()`.

### Impact on `mcp.py`

Each tool function calls the appropriate function from `github.py`, `data.py`, or `discover.py` directly.

### MCP Server Initialization

The MCP server resolves config and username once at startup (not per-tool-call):

```python
# mcp.py top-level setup
yaml_path = find_yaml_path()
repos = load_repos_from_yaml(yaml_path)
username = get_username()
```

These are module-level or cached in a startup function. Individual tool calls use the cached values. This avoids re-running `gh api user` on every invocation.

### Shared Constants

`IMPORTANT_REASONS` moves from `dashboard.py` to `data.py` since both the MCP notification filter and the dashboard renderer need it. `dashboard.py` imports it from `data.py`.

## Markdown Rendering

### New Function in `dashboard.py`

```python
def render_dashboard_markdown(data, show_all=False) -> str:
```

Returns a markdown string with the same sections and filtering as the terminal renderer:
- `## Notifications (N important)` (or `## Notifications (N)` with show_all)
- `## New Issues From Others (N)`
- `## Your Open PRs (N)`
- `## Recently Merged (N)`
- `## Other Activity`

Section headings match the terminal panel titles for consistency. Each section uses a markdown table. Empty sections are omitted.

## File Changes Summary

| File | Action |
|------|--------|
| `src/ghud/mcp.py` | Create — MCP server with 7 tools |
| `src/ghud/data.py` | Create — shared data-fetching logic |
| `src/ghud/config.py` | Modify — add XDG path, extract config home helper |
| `src/ghud/cli.py` | Modify — use data.py, add `serve` subcommand |
| `src/ghud/dashboard.py` | Modify — add `render_dashboard_markdown()` |
| `pyproject.toml` | Modify — add fastmcp dep, ghud-mcp entry point, bump to 0.2.0 |
| `tests/test_data.py` | Create |
| `tests/test_mcp.py` | Create |
| `tests/test_config.py` | Modify — add XDG path tests |
| `tests/test_dashboard.py` | Modify — add markdown rendering tests |
| `tests/test_cli.py` | Modify — add `serve` subcommand test |

## Out of Scope

- HTTP/SSE transport (fastmcp supports it, add later)
- HTML generation (v0.3.0)
- Repo filtering by category/org (future feature)
- Automatic config migration
