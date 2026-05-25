"""Resolve the portfolio repo list, from ~/.mrconfig or projects.yaml."""

import os
from typing import Optional

from ruamel.yaml import YAML

from ghud.mrconfig import find_mrconfig, parse_mrconfig

# Values of an .mrconfig `ghud =` key that opt a repo INTO / OUT OF the focused
# default listing. Owned repos are focused by default; externals are not.
_FOCUS_IN = {"track", "include", "focus", "show", "yes", "true", "on"}
_FOCUS_OUT = {"ignore", "exclude", "hide", "mute", "no", "false", "off"}

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


def load_repos_from_yaml(yaml_path: str, include_ignored: bool = False) -> list[str]:
    """Extract repo identifiers from projects.yaml.

    Skips the 'ignored' category unless include_ignored is set. Handles both
    nested (subcategories -> projects) and flat (projects) layouts. Skips
    projects that have no 'repo' field (e.g. academic projects with only 'url').
    """
    yaml = YAML()
    with open(yaml_path) as f:
        data = yaml.load(f)

    categories = data.get("categories", {})
    repos = []

    for cat_name, cat_data in categories.items():
        if cat_name == "ignored" and not include_ignored:
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


def _focus_mrconfig_repos(repos, username: Optional[str]) -> list[str]:
    """Filter parsed .mrconfig repos to the focused default set.

    A repo is focused when you own it (gh_repo owner == your username), unless
    its stanza has `ghud = ignore`. Externals (not owned by you) are excluded
    unless their stanza has `ghud = track`. If username is unknown we can't tell
    what you own, so we fall back to tag-only: just the explicitly-tracked repos.
    """
    user = (username or "").lower()
    selected: list[str] = []
    for r in repos:
        if not r.gh_repo:
            continue
        tag = (r.options.get("ghud") or "").strip().lower()
        if tag in _FOCUS_OUT:
            continue
        owned = bool(user) and (r.owner or "").lower() == user
        if owned or tag in _FOCUS_IN:
            selected.append(r.gh_repo)
    return selected


def resolve_portfolio(
    prefer_mrconfig: bool = True,
    focused: bool = True,
    username: Optional[str] = None,
) -> tuple[list[str], Optional[str]]:
    """Return (repos, source_path) for the portfolio.

    Prefers a myrepos ~/.mrconfig manifest when present (it's the
    version-controlled source of truth that `mr` already maintains), and falls
    back to projects.yaml. `repos` is a list of 'owner/repo' identifiers;
    `source_path` is the file they came from, or None if neither was found.

    When `focused` (the default), the listing is narrowed to the repos you
    actually want to watch: from .mrconfig that's repos you own plus any tagged
    `ghud = track`; from projects.yaml it's everything outside the `ignored`
    category. Pass focused=False for the full manifest. For .mrconfig focusing,
    `username` is your GitHub login; if omitted it's looked up via `gh`.
    """
    if prefer_mrconfig:
        mr_path = find_mrconfig()
        if mr_path is not None:
            repos = parse_mrconfig(mr_path)
            if focused:
                if username is None:
                    from ghud.github import get_username
                    username = get_username()
                result = _focus_mrconfig_repos(repos, username)
            else:
                result = [r.gh_repo for r in repos if r.gh_repo]
            return result, str(mr_path)

    yaml_path = find_yaml_path()
    if yaml_path is not None:
        return load_repos_from_yaml(yaml_path, include_ignored=not focused), yaml_path

    return [], None
