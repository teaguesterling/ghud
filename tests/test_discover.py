import json
import subprocess
import tempfile
import pytest
from ghud.discover import find_new_repos, format_new_project

SAMPLE_YAML = """\
# Portfolio Projects Configuration
site:
  github_username: testuser

categories:
  tools:
    title: "Tools"
    projects:
      - id: existing_tool
        name: "existing_tool"
        repo: testuser/existing_tool
        description: "Already tracked"
"""


def test_find_new_repos():
    github_repos = [
        {"nameWithOwner": "testuser/existing_tool", "description": "Already tracked", "name": "existing_tool"},
        {"nameWithOwner": "testuser/new_repo", "description": "Brand new", "name": "new_repo"},
        {"nameWithOwner": "testuser/another_new", "description": "Also new", "name": "another_new"},
    ]
    known_repos = ["testuser/existing_tool"]
    new = find_new_repos(github_repos, known_repos)
    assert len(new) == 2
    names = {r["nameWithOwner"] for r in new}
    assert "testuser/new_repo" in names
    assert "testuser/another_new" in names


def test_format_new_project():
    repo = {"nameWithOwner": "testuser/my-cool-repo", "description": "A cool repo", "name": "my-cool-repo"}
    project = format_new_project(repo)
    assert project["id"] == "my-cool-repo"
    assert project["repo"] == "testuser/my-cool-repo"
    assert project["description"] == "A cool repo"
