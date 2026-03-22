# ghud

**GitHub Heads-Up Display** — a terminal dashboard for your portfolio repos.

[![PyPI version](https://img.shields.io/pypi/v/ghud)](https://pypi.org/project/ghud/)
[![Documentation](https://readthedocs.org/projects/ghud/badge/?version=latest)](https://ghud.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

ghud gives you a single-command overview of your GitHub activity:

- **Important notifications** — review requests, mentions, assignments
- **Your open PRs** — with age and comment counts
- **Recently merged PRs** — what shipped this week
- **Issues from others** — on your portfolio repos
- **Other activity** — repos outside your portfolio

Plus a `discover` command to find repos missing from your portfolio config.

## Installation

```bash
pip install ghud
```

Requires the [GitHub CLI](https://cli.github.com/) (`gh`) to be installed and authenticated.

## Quick Start

```bash
# Show your dashboard
ghud

# Include low-priority notifications
ghud --all

# Extend merged-PR lookback to 30 days
ghud --days 30

# Find repos not yet in your portfolio config
ghud discover --dry-run
```

## Configuration

ghud reads a `projects.yaml` file that lists your portfolio repos. It checks these locations:

1. `~/Projects/pages/src/_data/projects.yaml`
2. `/mnt/aux-data/teague/Projects/pages/src/_data/projects.yaml`

The YAML uses a nested category/subcategory/project structure. Repos in the `ignored` category are excluded from the dashboard.

## Features

### Responsive Layout

On wide terminals (>=120 columns), ghud uses a two-column layout:
- **Left:** things needing your attention (notifications, issues from others)
- **Right:** your activity (open PRs, recently merged)

Narrow terminals get a single-column stack.

### Notification Filtering

By default, ghud shows only important notifications: `review_requested`, `mention`, `assign`, `team_mention`, `security_alert`. Use `--all` to include subscribed/comment notifications.

### Repo Discovery

`ghud discover` queries your GitHub account for all repos and compares against your `projects.yaml`. New repos are listed (with `--dry-run`) or added to an `uncategorized` section for you to organize.

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
