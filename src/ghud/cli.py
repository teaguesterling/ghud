"""CLI argument parsing and command dispatch."""

import argparse
import sys

from ghud.config import find_yaml_path, load_repos_from_yaml
from ghud.github import get_username
from ghud.data import fetch_dashboard_data
from ghud.dashboard import render_dashboard


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ghud",
        description="GitHub Heads-Up Display — terminal dashboard for your portfolio repos",
    )
    parser.add_argument("--all", action="store_true", help="Include all notifications")
    parser.add_argument("--days", type=int, default=7, help="Lookback days for merged PRs")

    subparsers = parser.add_subparsers(dest="command")

    discover_parser = subparsers.add_parser("discover", help="Discover new repos")
    discover_parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")

    subparsers.add_parser("serve", help="Run MCP server (stdio)")

    return parser.parse_args(argv)


def run_dashboard(args: argparse.Namespace) -> None:
    yaml_path = find_yaml_path()
    if not yaml_path:
        print("Error: Could not find projects.yaml", file=sys.stderr)
        sys.exit(1)

    repos = load_repos_from_yaml(yaml_path)
    username = get_username()

    if not username:
        print("Error: Could not determine GitHub username. Run 'gh auth login'.", file=sys.stderr)
        sys.exit(1)

    data = fetch_dashboard_data(repos, username, days=args.days)
    render_dashboard(data, show_all=args.all)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.command == "discover":
        from ghud.discover import run_discover
        run_discover(args)
    elif args.command == "serve":
        from ghud.mcp import main as mcp_main
        mcp_main()
    else:
        run_dashboard(args)
