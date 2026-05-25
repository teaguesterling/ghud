"""Tests for resolve_portfolio: source precedence and focus filtering."""

from ghud.config import resolve_portfolio

YAML = """\
categories:
  tools:
    projects:
      - id: foo
        repo: owner/foo
  ignored:
    projects:
      - id: noise
        repo: owner/noise
"""

# owned (mine/*), an external opted IN, an external left out, and an owned repo
# muted with ghud = ignore.
MRCONFIG = """\
[Projects/bar]
checkout = git clone git@github.com:mine/bar.git bar
skip = lazy

[Projects/tracked-ext]
checkout = git clone https://github.com/someone/tracked-ext.git tracked-ext
skip = lazy
ghud = track

[Projects/plain-ext]
checkout = git clone https://github.com/other/plain-ext.git plain-ext
skip = lazy

[Projects/muted]
checkout = git clone git@github.com:mine/muted.git muted
skip = lazy
ghud = ignore
"""


def _patch(monkeypatch, tmp_path, mr=True, yaml=True):
    mr_path = tmp_path / ".mrconfig"
    if mr:
        mr_path.write_text(MRCONFIG)
    yaml_path = tmp_path / "projects.yaml"
    if yaml:
        yaml_path.write_text(YAML)
    monkeypatch.setattr("ghud.config.find_mrconfig", lambda *a, **k: mr_path if mr else None)
    monkeypatch.setattr("ghud.config.find_yaml_path", lambda *a, **k: str(yaml_path) if yaml else None)
    return mr_path, yaml_path


def test_focused_mrconfig_owned_plus_tracked(tmp_path, monkeypatch):
    mr, _ = _patch(monkeypatch, tmp_path)
    repos, source = resolve_portfolio(username="mine")
    # owned (bar) + opted-in external (tracked-ext); muted and plain-ext excluded
    assert repos == ["mine/bar", "someone/tracked-ext"]
    assert source == str(mr)


def test_all_repos_returns_full_manifest(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    repos, _ = resolve_portfolio(focused=False, username="mine")
    assert repos == ["mine/bar", "someone/tracked-ext", "other/plain-ext", "mine/muted"]


def test_focus_without_username_is_tag_only(tmp_path, monkeypatch):
    # Can't tell ownership without a username -> only explicitly tracked repos.
    _patch(monkeypatch, tmp_path)
    repos, _ = resolve_portfolio(username="")
    assert repos == ["someone/tracked-ext"]


def test_focus_looks_up_username_when_omitted(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path)
    monkeypatch.setattr("ghud.github.get_username", lambda: "mine")
    repos, _ = resolve_portfolio()
    assert repos == ["mine/bar", "someone/tracked-ext"]


def test_prefers_mrconfig_over_yaml(tmp_path, monkeypatch):
    mr, _ = _patch(monkeypatch, tmp_path)
    repos, source = resolve_portfolio(username="mine")
    assert source == str(mr)
    assert "mine/bar" in repos  # from .mrconfig, not yaml's owner/foo
    assert "owner/foo" not in repos


def test_falls_back_to_yaml_when_no_mrconfig(tmp_path, monkeypatch):
    _, yaml = _patch(monkeypatch, tmp_path, mr=False)
    repos, source = resolve_portfolio(username="mine")
    assert repos == ["owner/foo"]  # ignored category skipped when focused
    assert source == str(yaml)


def test_yaml_all_repos_includes_ignored(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path, mr=False)
    repos, _ = resolve_portfolio(focused=False, username="mine")
    assert repos == ["owner/foo", "owner/noise"]


def test_prefer_mrconfig_false_uses_yaml(tmp_path, monkeypatch):
    _, yaml = _patch(monkeypatch, tmp_path)
    repos, source = resolve_portfolio(prefer_mrconfig=False, username="mine")
    assert repos == ["owner/foo"]
    assert source == str(yaml)


def test_none_when_neither_present(tmp_path, monkeypatch):
    _patch(monkeypatch, tmp_path, mr=False, yaml=False)
    repos, source = resolve_portfolio(username="mine")
    assert repos == []
    assert source is None
