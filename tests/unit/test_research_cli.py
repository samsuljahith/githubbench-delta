"""CLI help smoke tests for research subcommands."""

from __future__ import annotations

from typer.testing import CliRunner

from githubbench_delta.cli import app

runner = CliRunner()


def test_research_help():
    result = runner.invoke(app, ["research", "--help"])
    assert result.exit_code == 0
    for cmd in ("list", "status", "artifacts", "publish", "repro", "validate", "power"):
        assert cmd in result.stdout


def test_research_list():
    result = runner.invoke(app, ["research", "list"])
    assert result.exit_code == 0
    assert "E0a" in result.stdout
    assert "E1" in result.stdout
