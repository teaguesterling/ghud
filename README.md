# ghud

**GitHub Heads-Up Display** — a terminal dashboard for your portfolio repos.

[![PyPI version](https://img.shields.io/pypi/v/ghud)](https://pypi.org/project/ghud/)
[![Documentation](https://readthedocs.org/projects/ghud/badge/?version=latest)](https://ghud.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ghud gives you quick, formatted access to your GitHub activity without verbose `gh` field specifications or opening a browser.

- **Global dashboard** — notifications, open PRs, merged PRs, issues, other activity
- **Issue views** — `ghud i 42` for a rich issue display, `ghud i` for a list
- **PR views** — `ghud pr 15` with check status, reviews, and comments
- **Repo dashboard** — `ghud r` for issues + PRs in the current repo
- **Repo discovery** — find repos missing from your portfolio config

## Example

```
$ ghud
╭───────────────────────── New Issues From Others (3) ─────────────────────────╮
│  plinking_duck       Faster BCF/VCF reader for 'Free'              23d ago  │
│  duckdb_markdown     Would it be possible to add option to         50d ago  │
│                      write markdown with frontmatter data?                  │
│  duckdb_scalarfs     Curious about the extension usage             80d ago  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭───────────────────────────── Your Open PRs (5) ──────────────────────────────╮
│  community-ext       Update sitting_duck to v1.4.0                      0d  │
│  fledgling           Extract conversation tools into MCP server    13d  1c  │
│  fledgling           Fix ReadLines returning empty table           18d  1c  │
│  community-ext       Update plinking_duck to v0.1.2                    21d  │
│  duckdb_tarfs        Port to DuckDB v1.4-andium                   40d  3c  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Installation

```bash
pip install ghud
```

Requires the [GitHub CLI](https://cli.github.com/) (`gh`) to be installed and authenticated.

## Quick Start

```bash
# Global dashboard
ghud

# View issue #42 in the current repo
ghud i 42

# View PR #15 with full detail
ghud pr 15 --detail full

# List open issues across all portfolio repos
ghud i --repo all

# Repo dashboard for the current directory
ghud r

# Find repos not yet in your portfolio config
ghud discover --dry-run
```

## Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `ghud` / `ghud overview` | `ghud o` | Global dashboard |
| `ghud issue [N]` | `ghud i` | List issues or view detail |
| `ghud pr [N]` | | List PRs or view detail |
| `ghud repo` | `ghud r` | Repo-level dashboard |
| `ghud discover` | | Find untracked repos |
| `ghud serve` | | Start MCP server |

### Key Options

- `--repo owner/repo` — target a specific repo (`--repo all` for cross-repo)
- `--detail brief|summary|standard|full` — control detail level on issue/PR views
- `--comments N` — show last N comments (default: 3, or `--comments all`)
- `--no-pager` — disable pager
- `--state open|closed|all` — filter list views
- `--limit N` — max items in list views (default: 30)

## Configuration

ghud reads a `projects.yaml` file that lists your portfolio repos. It checks these locations:

1. `$XDG_CONFIG_HOME/ghud/projects.yaml` (default: `~/.config/ghud/projects.yaml`)
2. `~/Projects/pages/src/_data/projects.yaml`

The YAML uses a nested category/subcategory/project structure. Repos in the `ignored` category are excluded from the dashboard.

## Features

### Multi-View CLI

Browse issues, PRs, and repos with detail levels from brief (one-line summary) to full (body, all comments, timeline events, expanded CI checks).

### Check Status Indicators

PR views show CI and review status at a glance: `✓` passing, `✗` failing, `●` pending, `—` no checks.

### Auto Repo Detection

When run inside a git repo, ghud detects the repo from your `origin` remote. Override with `--repo` or use `--repo all` for cross-repo views.

### Responsive Layout

On wide terminals (>=120 columns), the dashboard uses a two-column layout. Narrow terminals get a single-column stack.

### MCP Server

`ghud serve` starts an MCP server exposing dashboard tools for AI agents, enabling integration with tools like Claude Code.

### Performance

ghud fetches all data in ~2 seconds using concurrent API calls and GraphQL batching for per-repo issue queries.

## Development

```bash
git clone https://github.com/teaguesterling/ghud.git
cd ghud
pip install -e ".[dev]"
pytest
```

## License

MIT
