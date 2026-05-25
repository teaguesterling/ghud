"""Repo discovery: find GitHub repos not yet in projects.yaml."""

import argparse
import json
import subprocess
import sys

from ghud.config import resolve_portfolio
from ghud.github import get_username
from ghud.mrconfig import find_mrconfig


def fetch_all_user_repos(username: str) -> list[dict]:
    """Fetch all repos the user owns or collaborates on."""
    repos = []
    # Owned repos
    result = subprocess.run(
        ["gh", "api", "--paginate", f"users/{username}/repos",
         "--jq", "[.[] | {nameWithOwner: .full_name, name: .name, description: .description, fork: .fork}]"],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split("\n"):
            try:
                repos.extend(json.loads(line))
            except json.JSONDecodeError:
                pass

    return repos


def find_new_repos(github_repos: list[dict], known_repos: list[str]) -> list[dict]:
    """Find repos present on GitHub but not in projects.yaml."""
    known_set = set(known_repos)
    return [r for r in github_repos if r["nameWithOwner"] not in known_set]


def format_new_project(repo: dict) -> dict:
    """Format a GitHub repo as a projects.yaml project entry."""
    name = repo.get("name", "")
    return {
        "id": name,
        "name": name,
        "repo": repo["nameWithOwner"],
        "description": repo.get("description") or "",
    }


def run_discover(args: argparse.Namespace) -> None:
    """Run the discover command."""
    known_repos, source = resolve_portfolio()
    if not source:
        print("Error: no portfolio found (~/.mrconfig or projects.yaml)", file=sys.stderr)
        sys.exit(1)

    # resolve_portfolio prefers .mrconfig, so if one exists it's the source.
    is_mrconfig = find_mrconfig() is not None

    username = get_username()
    if not username:
        print("Error: Could not determine GitHub username.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching repos for {username}...")
    github_repos = fetch_all_user_repos(username)
    new_repos = find_new_repos(github_repos, known_repos)

    if not new_repos:
        print(f"All repos are already tracked in {source}.")
        return

    print(f"\nFound {len(new_repos)} new repo(s) not in {source}:\n")
    for repo in sorted(new_repos, key=lambda r: r["nameWithOwner"]):
        desc = repo.get("description") or "(no description)"
        fork_label = " [fork]" if repo.get("fork") else ""
        print(f"  {repo['nameWithOwner']}{fork_label}")
        print(f"    {desc}")
        print()

    if args.dry_run:
        print("(dry run — no changes written)")
        return

    # The manifest is an .mrconfig — ghud can't write that meaningfully (mr owns
    # it). Print how to register them and stop.
    if is_mrconfig:
        print("Your portfolio is managed by myrepos (.mrconfig). Add repos with:")
        for repo in sorted(new_repos, key=lambda r: r["nameWithOwner"]):
            name = repo["nameWithOwner"].split("/")[-1]
            print(f"  cd ~/Projects/{name} && mr -c ~/.mrconfig register   # if checked out")
        print("\nOr hand-edit ~/.mrconfig (copy a stanza, swap name/URL), then commit your dotfiles.")
        return

    yaml_path = source

    # Append to YAML using ruamel.yaml to preserve formatting
    try:
        from ruamel.yaml import YAML
    except ImportError:
        print("Error: ruamel.yaml not installed. Run: pip install ruamel.yaml", file=sys.stderr)
        sys.exit(1)

    yaml = YAML()
    yaml.preserve_quotes = True

    with open(yaml_path) as f:
        data = yaml.load(f)

    categories = data.get("categories", {})

    # Create or get uncategorized section
    if "uncategorized" not in categories:
        categories["uncategorized"] = {
            "title": "Uncategorized",
            "description": "Newly discovered repos — move to appropriate categories",
            "projects": [],
        }

    uncategorized = categories["uncategorized"]
    if "projects" not in uncategorized:
        uncategorized["projects"] = []

    for repo in sorted(new_repos, key=lambda r: r["nameWithOwner"]):
        uncategorized["projects"].append(format_new_project(repo))

    with open(yaml_path, "w") as f:
        yaml.dump(data, f)

    print(f"Added {len(new_repos)} repo(s) to 'uncategorized' section in {yaml_path}")
    print("Move them to appropriate categories when ready.")
