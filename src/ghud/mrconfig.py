"""Parse a myrepos (`mr`) ~/.mrconfig file as a portfolio manifest.

`mr` (https://myrepos.branchable.com/) is a Perl tool, so there is no Python
package to depend on. This is a small, self-contained reader of just the parts
we need: the repo sections and their `checkout` clone URLs.

VENDORED: this module is duplicated verbatim in the `ffs` and `ghud` projects.
Keep the two copies in sync.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

# Match an owner/repo out of a github clone URL, SSH or HTTPS, with or without
# a trailing ".git":
#   git@github.com:teaguesterling/agent-riggs.git
#   https://github.com/45Drives/cockpit-file-sharing.git
_GH_URL_RE = re.compile(
    r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?(?:\s|$)"
)


@dataclass
class MrRepo:
    """One repo stanza from an .mrconfig file."""

    name: str  # last path component, e.g. "agent-riggs"
    section: str  # raw section header, e.g. "Projects/agent-riggs"
    path: Path  # resolved repo path (config dir / section)
    checkout: str | None = None  # raw `checkout =` command
    gh_repo: str | None = None  # "owner/repo" derived from the checkout URL
    skip: str | None = None  # value of `skip =` (e.g. "lazy")
    options: dict[str, str] = field(default_factory=dict)  # all raw stanza keys

    @property
    def exists(self) -> bool:
        """Whether the repo is actually checked out on this machine."""
        return self.path.is_dir()

    @property
    def owner(self) -> str | None:
        """The GitHub owner ('teaguesterling') from gh_repo, or None."""
        return self.gh_repo.split("/", 1)[0] if self.gh_repo else None


def gh_repo_from_checkout(checkout: str | None) -> str | None:
    """Extract an 'owner/repo' identifier from a checkout command, or None."""
    if not checkout:
        return None
    m = _GH_URL_RE.search(checkout)
    if not m:
        return None
    return f"{m.group('owner')}/{m.group('repo')}"


def find_mrconfig(candidates: list[str] | None = None) -> Path | None:
    """Return the first existing .mrconfig path, or None.

    Honors $MR_CONFIG, then falls back to ~/.mrconfig.
    """
    if candidates is None:
        candidates = []
        env = os.environ.get("MR_CONFIG")
        if env:
            candidates.append(env)
        candidates.append(os.path.expanduser("~/.mrconfig"))
    for c in candidates:
        p = Path(c).expanduser()
        if p.is_file():
            return p
    return None


def parse_mrconfig(path: str | os.PathLike) -> list[MrRepo]:
    """Parse an .mrconfig file into a list of MrRepo.

    The format is INI-like: `[section]` headers and `key = value` lines.
    Values may continue across following indented lines. We only need the
    `checkout` and `skip` keys, and we skip the `[DEFAULT]` section since it
    holds shared settings, not a repo. Section paths are resolved relative to
    the config file's directory (that's how `mr` interprets them).
    """
    path = Path(path)
    config_dir = path.parent
    repos: list[MrRepo] = []

    section: str | None = None
    keys: dict[str, str] = {}
    cur_key: str | None = None

    def flush() -> None:
        nonlocal section, keys
        if section and section != "DEFAULT":
            name = section.rsplit("/", 1)[-1]
            checkout = keys.get("checkout")
            repos.append(
                MrRepo(
                    name=name,
                    section=section,
                    path=(config_dir / section),
                    checkout=checkout,
                    gh_repo=gh_repo_from_checkout(checkout),
                    skip=keys.get("skip"),
                    options=dict(keys),
                )
            )
        section = None
        keys = {}

    for raw in Path(path).read_text().splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Section header
        if stripped.startswith("[") and stripped.endswith("]"):
            flush()
            section = stripped[1:-1].strip()
            cur_key = None
            continue
        if section is None:
            continue
        # Continuation line (indented, belongs to the previous key)
        if (line[:1] in (" ", "\t")) and cur_key is not None:
            keys[cur_key] += "\n" + stripped
            continue
        # key = value
        if "=" in line:
            key, _, value = line.partition("=")
            cur_key = key.strip()
            keys[cur_key] = value.strip()

    flush()
    return repos


def load_portfolio_repos(path: str | os.PathLike | None = None) -> list[str]:
    """Convenience: list of 'owner/repo' identifiers from an .mrconfig.

    Repos whose checkout URL isn't a recognizable GitHub repo are omitted.
    Returns [] if no config is found.
    """
    if path is None:
        path = find_mrconfig()
    if path is None:
        return []
    return [r.gh_repo for r in parse_mrconfig(path) if r.gh_repo]
