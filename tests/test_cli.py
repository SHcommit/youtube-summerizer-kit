import logging
import signal
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chew.cli import app
from chew.log import JsonFormatter


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


def test_cli_configures_json_logging_on_startup() -> None:
    # Remove any existing JsonFormatter handlers so the test is isolated
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if not isinstance(h.formatter, JsonFormatter)]

    runner = CliRunner()
    runner.invoke(app, ["doctor"])  # lightweight command that triggers callback

    json_handlers = [h for h in logging.getLogger().handlers if isinstance(h.formatter, JsonFormatter)]
    assert len(json_handlers) >= 1


def test_config_init_creates_editable_markdown_without_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    first = runner.invoke(app, ["설정", "--초기화"])
    original = (tmp_path / "CHEW.md").read_text(encoding="utf-8")
    second = runner.invoke(app, ["config", "--init"])

    assert first.exit_code == second.exit_code == 0
    assert (tmp_path / ".chew/profiles/blog.md").is_file()
    assert (tmp_path / "CHEW.md").read_text(encoding="utf-8") == original
    assert "preserved" in second.stdout


def test_sigterm_handler_is_registered_on_startup() -> None:
    from typer.testing import CliRunner

    from chew.cli.main import app as cli_app
    runner = CliRunner()
    runner.invoke(cli_app, ["doctor"])
    current_handler = signal.getsignal(signal.SIGTERM)
    assert current_handler not in (signal.SIG_DFL, None)
