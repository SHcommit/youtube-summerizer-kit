import logging
import signal
from importlib import import_module
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


def test_result_data_includes_usage() -> None:
    """_result_data() includes the usage dict when present."""
    from pathlib import Path

    from chew.app.service import CommandResult
    from chew.cli.main import _result_data

    result = CommandResult(
        run_id="run-1",
        profile="digest",
        reused=False,
        files=(Path("/tmp/out.md"),),
        usage={"input_tokens": 100, "output_tokens": 50},
    )
    data = _result_data(result)
    assert data["usage"] == {"input_tokens": 100, "output_tokens": 50}


def test_result_data_usage_none_when_not_set() -> None:
    """_result_data() usage is None when CommandResult.usage is None."""
    from pathlib import Path

    from chew.app.service import CommandResult
    from chew.cli.main import _result_data

    result = CommandResult(
        run_id="run-1",
        profile="digest",
        reused=False,
        files=(Path("/tmp/out.md"),),
    )
    data = _result_data(result)
    assert data["usage"] is None


def test_summarize_does_not_write_a_trace_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Normal user generation must not create maintainer trace artifacts."""
    from chew.app.service import CommandResult

    class FakeApplication:
        async def generate(self, *_: object, **__: object) -> CommandResult:
            return CommandResult(
                run_id="run-1",
                profile="digest",
                reused=False,
                files=(tmp_path / "output.md",),
            )

    cli_module = import_module("chew.cli.main")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_module, "_application_factory", lambda: FakeApplication())

    result = CliRunner().invoke(app, ["summarize", "https://youtu.be/example"])

    assert result.exit_code == 0
    assert not (tmp_path / "reports" / "trace_report.md").exists()


def test_summarize_rejects_transcript_without_source_url(tmp_path: Path) -> None:
    transcript = tmp_path / "captions.vtt"
    transcript.write_text("WEBVTT\n", encoding="utf-8")

    result = CliRunner().invoke(app, ["summarize", "--transcript", str(transcript)])

    assert result.exit_code == 2
    assert "--source-url" in result.stdout
