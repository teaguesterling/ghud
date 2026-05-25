"""Tests for resolve_portfolio: .mrconfig preferred, projects.yaml fallback."""

from pathlib import Path

from ghud.config import resolve_portfolio

YAML = """\
categories:
  tools:
    projects:
      - id: foo
        repo: owner/foo
"""

MRCONFIG = """\
[Projects/bar]
checkout = git clone git@github.com:owner/bar.git bar
skip = lazy
"""


def test_prefers_mrconfig_over_yaml(tmp_path, monkeypatch):
    mr = tmp_path / ".mrconfig"
    mr.write_text(MRCONFIG)
    yaml = tmp_path / "projects.yaml"
    yaml.write_text(YAML)
    monkeypatch.setattr("ghud.config.find_mrconfig", lambda *a, **k: mr)
    monkeypatch.setattr("ghud.config.find_yaml_path", lambda *a, **k: str(yaml))

    repos, source = resolve_portfolio()
    assert repos == ["owner/bar"]
    assert source == str(mr)


def test_falls_back_to_yaml_when_no_mrconfig(tmp_path, monkeypatch):
    yaml = tmp_path / "projects.yaml"
    yaml.write_text(YAML)
    monkeypatch.setattr("ghud.config.find_mrconfig", lambda *a, **k: None)
    monkeypatch.setattr("ghud.config.find_yaml_path", lambda *a, **k: str(yaml))

    repos, source = resolve_portfolio()
    assert repos == ["owner/foo"]
    assert source == str(yaml)


def test_prefer_mrconfig_false_uses_yaml(tmp_path, monkeypatch):
    mr = tmp_path / ".mrconfig"
    mr.write_text(MRCONFIG)
    yaml = tmp_path / "projects.yaml"
    yaml.write_text(YAML)
    monkeypatch.setattr("ghud.config.find_mrconfig", lambda *a, **k: mr)
    monkeypatch.setattr("ghud.config.find_yaml_path", lambda *a, **k: str(yaml))

    repos, source = resolve_portfolio(prefer_mrconfig=False)
    assert repos == ["owner/foo"]
    assert source == str(yaml)


def test_none_when_neither_present(monkeypatch):
    monkeypatch.setattr("ghud.config.find_mrconfig", lambda *a, **k: None)
    monkeypatch.setattr("ghud.config.find_yaml_path", lambda *a, **k: None)

    repos, source = resolve_portfolio()
    assert repos == []
    assert source is None
