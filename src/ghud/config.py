"""Load projects.yaml and extract portfolio repo identifiers."""

import os
from typing import Optional

from ruamel.yaml import YAML

# Default candidate paths for projects.yaml
DEFAULT_YAML_CANDIDATES = [
    os.path.expanduser("~/Projects/pages/src/_data/projects.yaml"),
    "/mnt/aux-data/teague/Projects/pages/src/_data/projects.yaml",
]


def find_yaml_path(candidates: Optional[list[str]] = None) -> Optional[str]:
    """Return the first existing candidate path, or None."""
    for path in (candidates or DEFAULT_YAML_CANDIDATES):
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
