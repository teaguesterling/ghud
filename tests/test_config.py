import tempfile
import os
import pytest
from ghud.config import find_yaml_path, load_repos_from_yaml

SAMPLE_YAML = """\
site:
  github_username: testuser

categories:
  extensions:
    title: "Extensions"
    subcategories:
      parsing:
        title: "Parsing"
        projects:
          - id: ext_a
            name: "ext_a"
            repo: testuser/ext_a
            description: "Extension A"
  tools:
    title: "Tools"
    projects:
      - id: tool_a
        name: "tool_a"
        repo: testuser/tool_a
        description: "Tool A"
      - id: academic_thing
        name: "Academic"
        url: "https://example.com"
        description: "No repo field"
  ignored:
    title: "Ignored"
    projects:
      - id: ignored_repo
        name: "ignored"
        repo: testuser/ignored_repo
        description: "Should be excluded"
"""


def test_load_repos_extracts_from_subcategories(tmp_path):
    yaml_file = tmp_path / "projects.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    repos = load_repos_from_yaml(str(yaml_file))
    assert "testuser/ext_a" in repos


def test_load_repos_extracts_from_direct_projects(tmp_path):
    yaml_file = tmp_path / "projects.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    repos = load_repos_from_yaml(str(yaml_file))
    assert "testuser/tool_a" in repos


def test_load_repos_skips_ignored_category(tmp_path):
    yaml_file = tmp_path / "projects.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    repos = load_repos_from_yaml(str(yaml_file))
    assert "testuser/ignored_repo" not in repos


def test_load_repos_skips_projects_without_repo(tmp_path):
    yaml_file = tmp_path / "projects.yaml"
    yaml_file.write_text(SAMPLE_YAML)
    repos = load_repos_from_yaml(str(yaml_file))
    # Should have exactly 2 repos (ext_a and tool_a), not academic_thing
    assert len(repos) == 2


def test_find_yaml_path_returns_first_existing(tmp_path):
    yaml_file = tmp_path / "projects.yaml"
    yaml_file.write_text("site: {}")
    path = find_yaml_path(candidates=[str(yaml_file), "/nonexistent/path"])
    assert path == str(yaml_file)


def test_find_yaml_path_returns_none_if_missing():
    path = find_yaml_path(candidates=["/nonexistent/a", "/nonexistent/b"])
    assert path is None


def test_find_yaml_path_checks_xdg_first(tmp_path, monkeypatch):
    xdg_dir = tmp_path / "xdg" / "ghud"
    xdg_dir.mkdir(parents=True)
    xdg_file = xdg_dir / "projects.yaml"
    xdg_file.write_text("site: {}")

    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    legacy_file = legacy_dir / "projects.yaml"
    legacy_file.write_text("site: {}")

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    from ghud.config import _build_yaml_candidates
    candidates = _build_yaml_candidates()
    assert candidates[0] == str(xdg_file)


def test_find_yaml_path_xdg_default_when_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    fake_home = str(tmp_path)
    monkeypatch.setattr(
        "os.path.expanduser",
        lambda p: p.replace("~", fake_home),
    )
    from ghud.config import _build_yaml_candidates
    candidates = _build_yaml_candidates()
    assert candidates[0].startswith(fake_home)
    assert "ghud" in candidates[0]
