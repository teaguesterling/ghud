import argparse
import json
import subprocess
import tempfile
import pytest
from ghud.discover import find_new_repos, format_new_project, run_discover

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


def test_run_discover_mrconfig_does_not_write_yaml(tmp_path, monkeypatch, capsys):
    """With an .mrconfig portfolio, discover prints mr hints, never writes yaml."""
    mr = tmp_path / ".mrconfig"
    mr.write_text(
        "[Projects/known]\n"
        "checkout = git clone git@github.com:testuser/known.git known\n"
    )
    monkeypatch.setattr("ghud.discover.resolve_portfolio",
                        lambda *a, **k: (["testuser/known"], str(mr)))
    monkeypatch.setattr("ghud.discover.find_mrconfig", lambda *a, **k: mr)
    monkeypatch.setattr("ghud.discover.get_username", lambda: "testuser")
    monkeypatch.setattr(
        "ghud.discover.fetch_all_user_repos",
        lambda u: [
            {"nameWithOwner": "testuser/known", "name": "known", "description": "", "fork": False},
            {"nameWithOwner": "testuser/newone", "name": "newone", "description": "", "fork": False},
        ],
    )
    before = mr.read_text()

    run_discover(argparse.Namespace(dry_run=False))

    out = capsys.readouterr().out
    assert "testuser/newone" in out
    assert "mr" in out and "register" in out  # printed registration hint
    assert mr.read_text() == before  # .mrconfig untouched
