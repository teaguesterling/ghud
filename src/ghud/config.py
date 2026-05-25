"""Resolve the portfolio repo list, from ~/.mrconfig or projects.yaml."""

import os
from typing import Optional

from ruamel.yaml import YAML

from ghud.mrconfig import find_mrconfig, load_portfolio_repos as _load_mrconfig_repos

# Legacy candidate paths for projects.yaml
_LEGACY_YAML_CANDIDATES = [
    os.path.expanduser("~/Projects/pages/src/_data/projects.yaml"),
    "/mnt/aux-data/teague/Projects/pages/src/_data/projects.yaml",
]


def _build_yaml_candidates() -> list[str]:
    """Build ordered list of candidate paths, XDG first."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    xdg_path = os.path.join(xdg_config, "ghud", "projects.yaml")
    return [xdg_path] + _LEGACY_YAML_CANDIDATES


def find_yaml_path(candidates: Optional[list[str]] = None) -> Optional[str]:
    """Return the first existing candidate path, or None."""
    for path in (candidates or _build_yaml_candidates()):
        if os.path.isfile(path):
            return path
    return None


def load_repos_from_yaml(yaml_path: str) -> list[str]:
    """Extract repo identifiers from projects.yaml, skipping 'ignored' category.

    Handles both nested (subcategories -> projects) and flat (projects) layouts.
    Skips projects that have no 'repo' field (e.g. academic projects with only 'url').
    """
    yaml = YAML()
    with open(yaml_path) as f:
        data = yaml.load(f)

    categories = data.get("categories", {})
    repos = []

    for cat_name, cat_data in categories.items():
        if cat_name == "ignored":
            continue
        if not isinstance(cat_data, dict):
            continue

        # Direct projects list
        for project in cat_data.get("projects", []):
            repo = project.get("repo")
            if repo:
                repos.append(repo)

        # Subcategories -> projects
        for sub_name, sub_data in cat_data.get("subcategories", {}).items():
            if not isinstance(sub_data, dict):
                continue
            for project in sub_data.get("projects", []):
                repo = project.get("repo")
                if repo:
                    repos.append(repo)

    return repos


def resolve_portfolio(prefer_mrconfig: bool = True) -> tuple[list[str], Optional[str]]:
    """Return (repos, source_path) for the portfolio.

    Prefers a myrepos ~/.mrconfig manifest when present (it's the
    version-controlled source of truth that `mr` already maintains), and falls
    back to projects.yaml. `repos` is a list of 'owner/repo' identifiers;
    `source_path` is the file they came from, or None if neither was found.
    """
    if prefer_mrconfig:
        mr_path = find_mrconfig()
        if mr_path is not None:
            return _load_mrconfig_repos(mr_path), str(mr_path)

    yaml_path = find_yaml_path()
    if yaml_path is not None:
        return load_repos_from_yaml(yaml_path), yaml_path

    return [], None
