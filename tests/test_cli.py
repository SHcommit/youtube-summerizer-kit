from pathlib import Path

import pytest
from typer.testing import CliRunner

from ytsum.cli import app


def test_help_exposes_english_commands_as_the_public_default() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "summarize" in result.stdout
    assert "config" in result.stdout
    assert "doctor" in result.stdout
    assert "status" in result.stdout
    assert "resume" in result.stdout
    assert "storage" in result.stdout
    assert "cleanup" in result.stdout
    assert "benchmark" in result.stdout
    assert "reusable knowledge" in result.stdout
    assert "local audio and video" in result.stdout


def test_korean_commands_remain_working_hidden_aliases() -> None:
    result = CliRunner().invoke(app, ["요약", "--help"])

    assert result.exit_code == 0
    assert "[source]" in result.stdout
    assert "YouTube URL or local audio/video path" in result.stdout


def test_benchmark_help_uses_english_subcommands_by_default() -> None:
    result = CliRunner().invoke(app, ["benchmark", "--help"])

    assert result.exit_code == 0
    assert "list" in result.stdout
    assert "results" in result.stdout
    assert "run" in result.stdout


def test_config_init_creates_editable_markdown_without_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    first = runner.invoke(app, ["설정", "--초기화"])
    original = (tmp_path / "YTSUM.md").read_text(encoding="utf-8")
    second = runner.invoke(app, ["config", "--init"])

    assert first.exit_code == second.exit_code == 0
    assert (tmp_path / ".ytsum/profiles/blog.md").is_file()
    assert (tmp_path / "YTSUM.md").read_text(encoding="utf-8") == original
    assert "preserved" in second.stdout
