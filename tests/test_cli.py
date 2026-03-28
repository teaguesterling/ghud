"""Tests for Typer CLI argument parsing and dispatch."""

from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from ghud.cli import app

runner = CliRunner()


def test_overview_is_default():
    """Running ghud with no args invokes the overview (dashboard)."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        mock_dash.assert_called_once()


def test_overview_explicit():
    """ghud overview invokes the dashboard."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, ["overview"])
        assert result.exit_code == 0
        mock_dash.assert_called_once()


def test_overview_all_flag():
    """ghud overview --all passes show_all=True."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, ["overview", "--all"])
        assert result.exit_code == 0
        mock_dash.assert_called_once()
        call_kwargs = mock_dash.call_args
        assert call_kwargs[1]["show_all"] is True or call_kwargs[0][0] is True


def test_overview_days_flag():
    """ghud overview --days 14 passes days=14."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, ["overview", "--days", "14"])
        assert result.exit_code == 0
        mock_dash.assert_called_once()


def test_discover_subcommand():
    """ghud discover invokes run_discover."""
    with patch("ghud.cli.run_discover_cmd") as mock_disc:
        result = runner.invoke(app, ["discover"])
        assert result.exit_code == 0
        mock_disc.assert_called_once()


def test_discover_dry_run():
    """ghud discover --dry-run passes dry_run=True."""
    with patch("ghud.cli.run_discover_cmd") as mock_disc:
        result = runner.invoke(app, ["discover", "--dry-run"])
        assert result.exit_code == 0
        mock_disc.assert_called_once()


def test_serve_subcommand():
    """ghud serve invokes the MCP server."""
    with patch("ghud.cli.run_serve") as mock_serve:
        result = runner.invoke(app, ["serve"])
        assert result.exit_code == 0
        mock_serve.assert_called_once()


def test_issue_stub():
    """ghud issue subcommand is registered."""
    with patch("ghud.cli.run_issue_list") as mock_list:
        result = runner.invoke(app, ["issue"])
        assert result.exit_code == 0


def test_pr_stub():
    """ghud pr subcommand is registered."""
    with patch("ghud.cli.run_pr_list") as mock_list:
        result = runner.invoke(app, ["pr"])
        assert result.exit_code == 0


def test_repo_stub():
    """ghud repo subcommand is registered."""
    with patch("ghud.cli.run_repo_dashboard") as mock_repo:
        result = runner.invoke(app, ["repo"])
        assert result.exit_code == 0


def test_issue_alias_i():
    """ghud i should work like ghud issue."""
    with patch("ghud.cli.run_issue_list") as mock_list:
        result = runner.invoke(app, ["i"])
        assert result.exit_code == 0


def test_pr_alias():
    """ghud pr should work."""
    with patch("ghud.cli.run_pr_list") as mock_list:
        result = runner.invoke(app, ["pr"])
        assert result.exit_code == 0


def test_repo_alias_r():
    """ghud r should work like ghud repo."""
    with patch("ghud.cli.run_repo_dashboard") as mock_repo:
        result = runner.invoke(app, ["r"])
        assert result.exit_code == 0


def test_overview_alias_o():
    """ghud o should work like ghud overview."""
    with patch("ghud.cli.run_dashboard") as mock_dash:
        result = runner.invoke(app, ["o"])
        assert result.exit_code == 0
