from pathlib import Path

from ghud.mrconfig import (
    find_mrconfig,
    gh_repo_from_checkout,
    load_portfolio_repos,
    parse_mrconfig,
)

SAMPLE = """\
# a comment
[DEFAULT]
git_update = git pull --ff-only "$@"

[Projects/agent-riggs]
checkout = git clone git@github.com:teaguesterling/agent-riggs.git agent-riggs
skip = lazy

[Projects/cockpit-file-sharing]
checkout = git clone https://github.com/45Drives/cockpit-file-sharing.git cockpit-file-sharing
skip = lazy

[Projects/no-suffix]
checkout = git clone git@github.com:teaguesterling/no-suffix no-suffix

[Projects/not-github]
checkout = git clone https://gitlab.com/someone/thing.git thing
"""


def _write(tmp_path):
    p = tmp_path / ".mrconfig"
    p.write_text(SAMPLE)
    return p


def test_gh_repo_from_checkout_variants():
    assert gh_repo_from_checkout("git clone git@github.com:o/r.git r") == "o/r"
    assert gh_repo_from_checkout("git clone https://github.com/o/r.git r") == "o/r"
    assert gh_repo_from_checkout("git clone git@github.com:o/r r") == "o/r"
    assert gh_repo_from_checkout("git clone https://gitlab.com/o/r.git r") is None
    assert gh_repo_from_checkout(None) is None


def test_parse_skips_default(tmp_path):
    names = [r.name for r in parse_mrconfig(_write(tmp_path))]
    assert names == ["agent-riggs", "cockpit-file-sharing", "no-suffix", "not-github"]


def test_load_portfolio_repos_filters_non_github(tmp_path):
    assert load_portfolio_repos(_write(tmp_path)) == [
        "teaguesterling/agent-riggs",
        "45Drives/cockpit-file-sharing",
        "teaguesterling/no-suffix",
    ]


def test_find_mrconfig_honors_env(tmp_path, monkeypatch):
    p = _write(tmp_path)
    monkeypatch.setenv("MR_CONFIG", str(p))
    assert find_mrconfig() == p
