# Changelog

## 0.2.0

### Added

- **Multi-view CLI** — new subcommands for browsing issues, PRs, and repos
  - `ghud issue` / `ghud i` — list issues or view issue detail (`ghud i 42`)
  - `ghud pr` — list PRs or view PR detail (`ghud pr 15`)
  - `ghud repo` / `ghud r` — repo-level dashboard showing issues + PRs
  - `ghud overview` / `ghud o` — explicit alias for the default dashboard
- **Detail levels** — `--detail brief|summary|standard|full` for issue and PR views
- **Check status indicators** — PRs show ✓/✗/●/— for CI checks and review status
- **Repo context detection** — auto-detects repo from git remote; override with `--repo`
- **Comment display** — shows last 3 comments by default; `--comments N` or `--comments all`
- **Pager support** — output pipes through a pager by default; `--no-pager` to disable
- **Subcommand aliases** — `i` for issue, `o` for overview, `r` for repo
- **Typer CLI framework** — replaced argparse with Typer for better help and extensibility
- **MCP server** — `ghud serve` starts an MCP server exposing dashboard tools for AI agents

### Changed

- CLI framework migrated from argparse to Typer
- Configuration now checks XDG_CONFIG_HOME first (`~/.config/ghud/projects.yaml`)

## 0.1.0

### Added

- Initial release
- Global dashboard with notifications, open PRs, merged PRs, issues, and other activity
- `ghud discover` command for finding untracked repos
- Portfolio configuration via `projects.yaml`
- Responsive two-column terminal layout
- GraphQL batching for fast issue queries
