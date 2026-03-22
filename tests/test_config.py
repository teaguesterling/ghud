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
