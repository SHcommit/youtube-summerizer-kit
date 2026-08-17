from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chew.application import AuthenticationRequired, CommandResult, RunStatus
from chew.cli import app, normalize_cli_args
from chew.config import ConfigurationError
from chew.identity import SourceInputError
from chew.transcripts.service import TranscriptUnavailable
from chew.transcripts.whisper import WhisperDependencyMissing

URL = "https://youtu.be/abcDEF_1234"


@dataclass
class StubApplication:
    calls: list[tuple[str, str]] = field(default_factory=list)
    error: Exception | None = None
    resume_error: Exception | None = None

    async def generate(
        self, url: str, profile: str, destination: Path, depth: str | None = None
    ) -> CommandResult:
        self.calls.append((url, profile))
        if self.error is not None:
            raise self.error
        return CommandResult("run-1", profile, True, (destination / "index.md",))

    def status(self, run_id: str | None = None) -> tuple[RunStatus, ...]:
        return (RunStatus(run_id or "run-1", "youtube:abcDEF_1234", "completed", 4, 4),)

    async def resume(self, run_id: str | None = None) -> CommandResult:
        if self.resume_error is not None:
            raise self.resume_error
        return CommandResult(run_id or "run-1", "digest", False, ())

    def diagnostics(self) -> dict[str, object]:
        return {"runtimes": [{"id": "codex", "available": True}]}


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch) -> StubApplication:
    value = StubApplication()
    monkeypatch.setattr("chew.cli._application_factory", lambda: value)
    return value


def test_bare_youtube_url_becomes_default_summary_command() -> None:
    assert normalize_cli_args([URL]) == ["summarize", URL]
    mobile = "https://m.youtube.com/watch?v=abcDEF_1234"
    assert normalize_cli_args([mobile]) == ["summarize", mobile]


def test_bare_local_media_path_becomes_default_summary_command(tmp_path: Path) -> None:
    media = tmp_path / "meeting.mp3"
    media.write_bytes(b"audio")

    assert normalize_cli_args([str(media)]) == ["summarize", str(media)]


@pytest.mark.parametrize(
    ("command", "profile"),
    [("블로그", "blog"), ("study", "study"), ("옵시디언", "obsidian")],
)
def test_output_commands_reuse_analysis_by_url(
    stub: StubApplication, tmp_path: Path, command: str, profile: str
) -> None:
    result = CliRunner().invoke(app, [command, URL, "--output", str(tmp_path)])
    assert result.exit_code == 0
    assert stub.calls == [(URL, profile)]
    expected = "기존 분석 재사용" if command in {"블로그", "옵시디언"} else "reused analysis"
    assert expected in result.stdout


def test_missing_url_uses_interactive_prompt(stub: StubApplication, tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["요약", "--output", str(tmp_path)],
        input=f"{URL}\n",
    )
    assert result.exit_code == 0
    assert stub.calls == [(URL, "digest")]


def test_authentication_failure_is_actionable(stub: StubApplication, tmp_path: Path) -> None:
    stub.error = AuthenticationRequired("codex", "codex login")
    result = CliRunner().invoke(app, ["요약", URL, "--output", str(tmp_path)])
    assert result.exit_code == 2
    assert "codex login" in result.stdout


def test_english_authentication_failure_is_in_english(
    stub: StubApplication, tmp_path: Path
) -> None:
    stub.error = AuthenticationRequired("codex", "codex login")
    result = CliRunner().invoke(app, ["summarize", URL, "--output", str(tmp_path)])
    assert result.exit_code == 2
    assert "Authentication required" in result.stdout
    assert "codex login" in result.stdout


def test_configuration_errors_follow_the_invoked_command_language(
    stub: StubApplication, tmp_path: Path
) -> None:
    stub.error = ConfigurationError("Invalid YAML front matter in YTSUM.md")

    english = CliRunner().invoke(app, ["summarize", URL, "--output", str(tmp_path)])
    korean = CliRunner().invoke(app, ["요약", URL, "--output", str(tmp_path)])

    assert english.exit_code == korean.exit_code == 2
    assert "Configuration error" in english.stdout
    assert "설정 오류" in korean.stdout


def test_local_media_input_errors_follow_the_invoked_command_language(
    stub: StubApplication, tmp_path: Path
) -> None:
    stub.error = SourceInputError("local media file not found")

    english = CliRunner().invoke(app, ["summarize", "missing.mp3", "--output", str(tmp_path)])
    korean = CliRunner().invoke(app, ["요약", "missing.mp3", "--output", str(tmp_path)])

    assert english.exit_code == korean.exit_code == 2
    assert "Local media error" in english.stdout
    assert "로컬 미디어 오류" in korean.stdout


def test_missing_captions_explain_how_to_enable_local_audio_transcription(
    stub: StubApplication, tmp_path: Path
) -> None:
    stub.error = TranscriptUnavailable(())

    english = CliRunner().invoke(app, ["summarize", URL, "--output", str(tmp_path)])
    korean = CliRunner().invoke(app, ["요약", URL, "--output", str(tmp_path)])

    assert english.exit_code == korean.exit_code == 2
    assert "No usable captions" in english.stdout
    assert "사용 가능한 자막" in korean.stdout
    assert "whisper_fallback: true" in english.stdout
    assert "whisper_fallback: true" in korean.stdout
    assert ".[youtube,whisper]" in english.stdout


def test_missing_whisper_dependency_has_bilingual_install_guidance(
    stub: StubApplication, tmp_path: Path
) -> None:
    stub.error = WhisperDependencyMissing("faster-whisper is not installed")

    english = CliRunner().invoke(app, ["summarize", URL, "--output", str(tmp_path)])
    korean = CliRunner().invoke(app, ["요약", URL, "--output", str(tmp_path)])

    assert english.exit_code == korean.exit_code == 2
    assert "Whisper fallback is enabled" in english.stdout
    assert "Whisper fallback이 활성화" in korean.stdout
    assert ".[youtube,whisper]" in english.stdout + korean.stdout


def test_local_media_transcription_errors_do_not_suggest_enabling_youtube_fallback(
    stub: StubApplication, tmp_path: Path
) -> None:
    local_source = "recording.mp3"
    stub.error = TranscriptUnavailable(())

    no_speech = CliRunner().invoke(app, ["summarize", local_source, "--output", str(tmp_path)])

    assert no_speech.exit_code == 2
    assert "No usable speech transcript" in no_speech.stdout
    assert "whisper_fallback" not in no_speech.stdout

    stub.error = WhisperDependencyMissing("faster-whisper is not installed")
    missing_dependency = CliRunner().invoke(
        app, ["summarize", local_source, "--output", str(tmp_path)]
    )

    assert missing_dependency.exit_code == 2
    assert "Local media transcription requires" in missing_dependency.stdout
    assert ".[youtube,whisper]" in missing_dependency.stdout


def test_json_output_has_stable_envelope(stub: StubApplication, tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["summarize", URL, "--output", str(tmp_path), "--json"],
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "data": {
            "files": [str(tmp_path / "index.md")],
            "profile": "digest",
            "reused": True,
            "run_id": "run-1",
        },
        "ok": True,
    }


def test_status_and_resume_have_human_aliases(stub: StubApplication) -> None:
    status = CliRunner().invoke(app, ["상태", "--json"])
    resumed = CliRunner().invoke(app, ["resume", "run-1", "--json"])
    assert status.exit_code == resumed.exit_code == 0
    assert json.loads(status.stdout)["data"][0]["run_id"] == "run-1"
    assert json.loads(resumed.stdout)["data"]["run_id"] == "run-1"


def test_english_status_and_doctor_are_human_readable(stub: StubApplication) -> None:
    status = CliRunner().invoke(app, ["status"])
    doctor = CliRunner().invoke(app, ["doctor"])

    assert status.exit_code == doctor.exit_code == 0
    assert "run-1" in status.stdout
    assert "4/4 jobs" in status.stdout
    assert "codex: available" in doctor.stdout
    assert not status.stdout.lstrip().startswith("[")
    assert not doctor.stdout.lstrip().startswith("{")


def test_resume_errors_follow_the_invoked_command_language(stub: StubApplication) -> None:
    stub.resume_error = LookupError("No resumable analysis was found.")

    english = CliRunner().invoke(app, ["resume"])
    korean = CliRunner().invoke(app, ["이어하기"])

    assert english.exit_code == korean.exit_code == 1
    assert "No resumable analysis" in english.stdout
    assert "이어갈 분석" in korean.stdout


def test_resume_authentication_guidance_follows_the_invoked_command_language(
    stub: StubApplication,
) -> None:
    stub.resume_error = AuthenticationRequired("codex", "codex login")

    english = CliRunner().invoke(app, ["resume"])
    korean = CliRunner().invoke(app, ["이어하기"])

    assert english.exit_code == korean.exit_code == 2
    assert "Authentication required" in english.stdout
    assert "로그인이 필요" in korean.stdout
    assert "codex login" in english.stdout + korean.stdout
