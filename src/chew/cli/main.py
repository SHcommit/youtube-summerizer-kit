"""Short Korean and English command workflows."""

from __future__ import annotations

import asyncio
import json
import signal as _signal
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any, Protocol, cast

import typer

from chew.app.config import ConfigurationError
from chew.app.retention import CleanupPlan, RetentionPlanner
from chew.app.service import AuthenticationRequired, CommandResult, RunStatus
from chew.benchmark.runner import (
    BenchmarkReference,
    BenchmarkRunner,
    benchmark_catalog,
    live_benchmark_spec,
    write_benchmark_report,
)
from chew.core.identity import (
    SourceInputError,
    looks_like_local_media_input,
    normalize_youtube_url,
)
from chew.log import configure_logging
from chew.telemetry import telemetry
from chew.transcripts.service import TranscriptUnavailable
from chew.transcripts.whisper import WhisperDependencyMissing


class Application(Protocol):
    async def generate(self, url: str, profile: str, destination: Path, depth: str | None = None) -> CommandResult: ...

    def status(self, run_id: str | None = None) -> tuple[RunStatus, ...]: ...

    async def resume(self, run_id: str | None = None) -> CommandResult: ...

    def diagnostics(self) -> dict[str, object]: ...


app = typer.Typer(
    name="chew",
    help=("Turn YouTube videos and local audio and video files into reusable knowledge packs and documents."),
    no_args_is_help=True,
    rich_markup_mode=None,
)


@app.callback()
def _startup(
    log_level: str = typer.Option(
        "WARNING",
        envvar="CHEW_LOG_LEVEL",
        hidden=True,
        help="Log level for structured JSON output (DEBUG/INFO/WARNING/ERROR).",
    ),
) -> None:
    configure_logging(level=log_level)

    def _handle_sigterm(signum: int, frame: object) -> None:
        raise KeyboardInterrupt

    _signal.signal(_signal.SIGTERM, _handle_sigterm)


def _application_factory() -> Application:
    cli_mod = sys.modules.get("chew.cli")
    if cli_mod is not None and getattr(cli_mod, "_application_factory", None) not in (
        None,
        _application_factory,
    ):
        return cast(Application, cli_mod._application_factory())
    from chew.app.bootstrap import build_application

    return build_application()


def _retention_factory() -> RetentionPlanner:
    cli_mod = sys.modules.get("chew.cli")
    if cli_mod is not None and getattr(cli_mod, "_retention_factory", None) not in (
        None,
        _retention_factory,
    ):
        return cast(RetentionPlanner, cli_mod._retention_factory())
    from chew.app.bootstrap import build_retention_planner

    return build_retention_planner()


KOREAN_COMMANDS = {
    "요약",
    "블로그",
    "학습",
    "옵시디언",
    "상태",
    "이어하기",
    "설정",
    "진단",
    "저장소",
    "정리",
    "삭제",
    "완전삭제",
    "벤치마크",
    "목록",
    "결과",
    "실행",
}


def _is_korean(context: typer.Context) -> bool:
    return context.info_name in KOREAN_COMMANDS


def _emit(data: Any, json_output: bool, *, korean: bool = False) -> None:
    if json_output:
        typer.echo(json.dumps({"ok": True, "data": data}, ensure_ascii=False, sort_keys=True))
        return
    if isinstance(data, dict) and "run_id" in data:
        reuse = (" · 기존 분석 재사용" if korean else " · reused analysis") if data.get("reused") else ""
        label = "완료" if korean else "Completed"
        typer.echo(f"{label}: {data['run_id']}{reuse}")
        for path in data.get("files", []):
            typer.echo(path)
        usage = data.get("usage")
        if isinstance(usage, dict) and not data.get("reused"):
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            if korean:
                typer.echo(f"토큰 사용량: 입력 {input_tokens:,} / 출력 {output_tokens:,}")
            else:
                typer.echo(f"Token usage: {input_tokens:,} input / {output_tokens:,} output")
    else:
        typer.echo(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False))


def _result_data(result: CommandResult) -> dict[str, object]:
    return {
        "run_id": result.run_id,
        "profile": result.profile,
        "reused": result.reused,
        "files": [str(path) for path in result.files],
        "usage": result.usage,
    }


def _emit_status(values: list[dict[str, object]], json_output: bool, *, korean: bool) -> None:
    if json_output:
        _emit(values, True)
        return
    if not values:
        typer.echo("분석 기록이 없습니다." if korean else "No analysis runs found.")
        return
    for value in values:
        jobs = f"{value['completed_jobs']}/{value['total_jobs']}"
        suffix = "작업" if korean else "jobs"
        typer.echo(f"{value['run_id']}  {value['status']}  {jobs} {suffix}  {value['source_id']}")


def _emit_diagnostics(data: dict[str, object], json_output: bool, *, korean: bool) -> None:
    if json_output:
        _emit(data, True)
        return
    runtimes = data.get("runtimes")
    if not isinstance(runtimes, list):
        _emit(data, False, korean=korean)
        return
    for runtime in runtimes:
        if not isinstance(runtime, dict):
            continue
        runtime_id = runtime.get("runtime_id", runtime.get("id", "unknown"))
        available = bool(runtime.get("available"))
        auth_ready = runtime.get("auth_ready")
        if korean:
            state = "사용 가능" if available else "설치되지 않음"
            auth = " · 인증됨" if auth_ready is True else " · 인증 필요" if auth_ready is False else ""
        else:
            state = "available" if available else "not installed"
            auth = (
                " · authenticated"
                if auth_ready is True
                else " · authentication required"
                if auth_ready is False
                else ""
            )
        typer.echo(f"{runtime_id}: {state}{auth}")


def _emit_authentication_error(error: AuthenticationRequired, *, korean: bool) -> None:
    if korean:
        typer.echo(f"{error.runtime_id} 로그인이 필요합니다. 실행: {error.login_command}")
    else:
        typer.echo(str(error))


def _run_generation(
    context: typer.Context,
    source: str | None,
    profile: str,
    output: Path,
    json_output: bool,
    depth: str | None = None,
) -> None:
    korean = _is_korean(context)
    selected_source = source or typer.prompt(
        "YouTube URL 또는 로컬 오디오/영상 경로" if korean else "YouTube URL or local audio/video path"
    )
    local_media = looks_like_local_media_input(selected_source)
    try:
        result = asyncio.run(_application_factory().generate(selected_source, profile, output, depth=depth))
    except KeyboardInterrupt:
        label = "작업이 사용자에 의해 중단되었습니다." if korean else "Operation cancelled by user."
        typer.echo(f"\n{label}")
        raise typer.Exit(130) from None
    except AuthenticationRequired as error:
        _emit_authentication_error(error, korean=korean)
        raise typer.Exit(2) from error
    except ConfigurationError as error:
        label = "설정 오류" if korean else "Configuration error"
        typer.echo(f"{label}: {error}")
        raise typer.Exit(2) from error
    except SourceInputError as error:
        label = "로컬 미디어 오류" if korean else "Local media error"
        typer.echo(f"{label}: {error}")
        raise typer.Exit(2) from error
    except TranscriptUnavailable as error:
        if korean and local_media:
            typer.echo(
                "사용 가능한 음성 transcript를 만들지 못했습니다. 파일에 음성이 있는지와 오디오 품질을 확인하세요."
            )
        elif local_media:
            typer.echo(
                "No usable speech transcript could be created. Check that the file contains "
                "speech and that its audio is readable."
            )
        elif korean:
            typer.echo(
                "사용 가능한 자막이 없습니다. 영상 오디오를 로컬에서 음성 인식하려면 "
                "`pip install -e '.[youtube,whisper]'`를 실행하고 CHEW.md에 "
                "`whisper_fallback: true`를 설정하세요."
            )
        else:
            typer.echo(
                "No usable captions were found. To transcribe the video audio locally, run "
                "`pip install -e '.[youtube,whisper]'` and set `whisper_fallback: true` "
                "in CHEW.md."
            )
        raise typer.Exit(2) from error
    except WhisperDependencyMissing as error:
        if korean and local_media:
            typer.echo(
                "로컬 미디어 음성 인식에는 Whisper 선택 의존성이 필요합니다. "
                "`pip install -e '.[youtube,whisper]'`를 실행하세요."
            )
        elif local_media:
            typer.echo(
                "Local media transcription requires the optional Whisper dependencies. "
                "Run `pip install -e '.[youtube,whisper]'`."
            )
        elif korean:
            typer.echo(
                "Whisper fallback이 활성화되어 있지만 선택적 의존성이 없습니다. "
                "`pip install -e '.[youtube,whisper]'`를 실행하세요."
            )
        else:
            typer.echo(
                "Whisper fallback is enabled, but its optional dependencies are missing. "
                "Run `pip install -e '.[youtube,whisper]'`."
            )
        raise typer.Exit(2) from error
    try:
        exported_report = telemetry.export_markdown_report("reports/trace_report.md")
        if not json_output:
            typer.echo(f"OpenTelemetry Trace Report: file://{exported_report.resolve()}")
    except Exception:
        pass
    _emit(_result_data(result), json_output, korean=korean)


def summarize(
    context: typer.Context,
    source: Annotated[str | None, typer.Argument(help="YouTube URL or local audio/video path")] = None,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("chew-output"),
    json_output: Annotated[bool, typer.Option("--json")] = False,
    depth: Annotated[
        str | None,
        typer.Option("--depth", "--요약강도", "-d", help="Summary intensity: quick (short/brief), detailed, deep"),
    ] = None,
) -> None:
    """Create a detailed digest from a video."""
    _run_generation(context, source, "digest", output, json_output, depth=depth)


def blog(
    context: typer.Context,
    source: Annotated[str | None, typer.Argument(help="YouTube URL or local audio/video path")] = None,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("chew-blog"),
    json_output: Annotated[bool, typer.Option("--json")] = False,
    depth: Annotated[
        str | None,
        typer.Option("--depth", "--요약강도", "-d", help="Summary intensity: quick (short/brief), detailed, deep"),
    ] = None,
) -> None:
    """설정한 문체로 블로그 글을 만듭니다."""
    _run_generation(context, source, "blog", output, json_output, depth=depth)


def study(
    context: typer.Context,
    source: Annotated[str | None, typer.Argument(help="YouTube URL or local audio/video path")] = None,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("chew-study"),
    json_output: Annotated[bool, typer.Option("--json")] = False,
    depth: Annotated[
        str | None,
        typer.Option("--depth", "--요약강도", "-d", help="Summary intensity: quick (short/brief), detailed, deep"),
    ] = None,
) -> None:
    """학습 노트와 추가 학습 항목을 만듭니다."""
    _run_generation(context, source, "study", output, json_output, depth=depth)


def obsidian(
    context: typer.Context,
    source: Annotated[str | None, typer.Argument(help="YouTube URL or local audio/video path")] = None,
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("chew-vault"),
    json_output: Annotated[bool, typer.Option("--json")] = False,
    depth: Annotated[
        str | None,
        typer.Option("--depth", "--요약강도", "-d", help="Summary intensity: quick (short/brief), detailed, deep"),
    ] = None,
) -> None:
    """위키링크가 포함된 Obsidian 노트를 만듭니다."""
    _run_generation(context, source, "obsidian", output, json_output, depth=depth)


for english, korean, help_text, command in (
    ("summarize", "요약", "Create a detailed digest.", summarize),
    ("blog", "블로그", "Create a post using the configured voice.", blog),
    ("study", "학습", "Create study notes and follow-up topics.", study),
    ("obsidian", "옵시디언", "Create an Obsidian vault with wikilinks.", obsidian),
):
    app.command(english, help=help_text)(command)
    app.command(korean, hidden=True)(command)


def status(
    context: typer.Context,
    run_id: Annotated[str | None, typer.Argument()] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    values = [asdict(value) for value in _application_factory().status(run_id)]
    _emit_status(values, json_output, korean=_is_korean(context))


app.command("status", help="Show analysis and job progress.")(status)
app.command("상태", hidden=True)(status)


def trace_ui(
    context: typer.Context,
    open_browser: Annotated[bool, typer.Option("--open/--no-open", "-b")] = True,
) -> None:
    """OpenTelemetry visual performance & tracing web UI dashboard."""
    report_path = telemetry.export_markdown_report("reports/trace_report.md")
    abs_path = report_path.resolve()
    typer.echo(f"OpenTelemetry Trace Report: file://{abs_path}")
    typer.echo("Jaeger OpenTelemetry UI: http://localhost:16686")
    if open_browser:
        import webbrowser

        webbrowser.open("http://localhost:16686")


app.command("dashboard", help="Open OpenTelemetry visual performance UI dashboard.")(trace_ui)
app.command("ui", help="Open OpenTelemetry visual performance UI dashboard.")(trace_ui)
app.command("benchmark-dashboard", help="Open OpenTelemetry visual performance UI dashboard.")(trace_ui)
app.command("benchmark-ui", help="Open OpenTelemetry visual performance UI dashboard.")(trace_ui)
app.command("대시보드", hidden=True)(trace_ui)


def resume(
    context: typer.Context,
    run_id: Annotated[str | None, typer.Argument()] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    try:
        result = asyncio.run(_application_factory().resume(run_id))
    except AuthenticationRequired as error:
        _emit_authentication_error(error, korean=_is_korean(context))
        raise typer.Exit(2) from error
    except LookupError as error:
        typer.echo("이어갈 분석이 없습니다." if _is_korean(context) else str(error))
        raise typer.Exit(1) from error
    _emit(_result_data(result), json_output, korean=_is_korean(context))


app.command("resume", help="Resume an interrupted analysis.")(resume)
app.command("이어하기", hidden=True)(resume)


def config(
    context: typer.Context,
    initialize: Annotated[bool, typer.Option("--초기화", "--init")] = False,
) -> None:
    if initialize:
        targets = (
            ("CHEW.md", Path("CHEW.md")),
            ("profiles/blog.md", Path(".chew/profiles/blog.md")),
            ("profiles/study.md", Path(".chew/profiles/study.md")),
            ("profiles/obsidian.md", Path(".chew/profiles/obsidian.md")),
        )
        created: list[Path] = []
        templates = files("chew.templates")
        for resource, destination in targets:
            if destination.exists():
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            resource_name = "CHEW.md" if resource == "CHEW.md" else resource
            try:
                content = templates.joinpath(resource_name).read_text(encoding="utf-8")
            except TypeError:
                content = templates.joinpath("YTSUM.md").read_text(encoding="utf-8")
            destination.write_text(content, encoding="utf-8")
            created.append(destination)
        if created:
            label = "생성" if _is_korean(context) else "Created"
            typer.echo(f"{label}: " + ", ".join(str(path) for path in created))
        else:
            typer.echo(
                "기존 설정 파일을 유지했습니다."
                if _is_korean(context)
                else "Existing configuration files were preserved."
            )
        return
    typer.echo(
        "프로젝트 루트의 CHEW.md와 .chew/profiles/*.md를 편집하세요."
        if _is_korean(context)
        else "Edit CHEW.md and .chew/profiles/*.md in the project root."
    )


app.command("config", help="Show or initialize Markdown configuration.")(config)
app.command("설정", hidden=True)(config)


def doctor(
    context: typer.Context,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _emit_diagnostics(_application_factory().diagnostics(), json_output, korean=_is_korean(context))


app.command("doctor", help="Diagnose AI runtime installation and authentication.")(doctor)
app.command("진단", hidden=True)(doctor)


def _plan_data(plan: CleanupPlan) -> dict[str, object]:
    return {
        "policy": plan.policy,
        "created_at": plan.created_at.isoformat(),
        "run_ids": list(plan.run_ids),
        "items": [{"path": str(item.path), "reason": item.reason, "size": item.size} for item in plan.items],
    }


def storage(
    context: typer.Context,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _emit(_retention_factory().usage(), json_output, korean=_is_korean(context))


app.command("storage", help="Show internal storage usage.")(storage)
app.command("저장소", hidden=True)(storage)


def cleanup(
    context: typer.Context,
    policy: Annotated[str, typer.Option("--policy")] = "compact",
    apply_changes: Annotated[bool, typer.Option("--apply")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    planner = _retention_factory()
    plan = planner.preview(datetime.now(UTC), policy)
    if apply_changes:
        result = planner.apply(plan)
        _emit(asdict(result), json_output, korean=_is_korean(context))
    else:
        _emit(_plan_data(plan), json_output, korean=_is_korean(context))


app.command("cleanup", help="Preview or apply a retention policy.")(cleanup)
app.command("정리", hidden=True)(cleanup)


def delete(
    context: typer.Context,
    target: Annotated[str, typer.Argument()],
    yes: Annotated[bool, typer.Option("--yes", "-y")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    planner = _retention_factory()
    plan = planner.delete_target(target)
    if not yes:
        typer.echo(json.dumps(_plan_data(plan), ensure_ascii=False))
        phrase = "삭제" if _is_korean(context) else "delete"
        prompt = "삭제하려면 '삭제'를 입력하세요" if _is_korean(context) else "Type 'delete' to continue"
        if typer.prompt(prompt) != phrase:
            raise typer.Exit(1)
    _emit(asdict(planner.apply(plan)), json_output, korean=_is_korean(context))


app.command("delete", help="Delete internal data for a run or video.")(delete)
app.command("삭제", hidden=True)(delete)


def purge(
    context: typer.Context,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    phrase = "완전삭제" if _is_korean(context) else "purge"
    prompt = (
        "모든 내부 데이터를 지우려면 '완전삭제'를 입력하세요"
        if _is_korean(context)
        else "Type 'purge' to remove all internal data"
    )
    if typer.prompt(prompt) != phrase:
        raise typer.Exit(1)
    _emit(asdict(_retention_factory().purge()), json_output, korean=_is_korean(context))


app.command("purge", help="Remove all internal data except exported documents.")(purge)
app.command("완전삭제", hidden=True)(purge)


benchmark_commands = typer.Typer(
    help="Compare direct video analysis with the hierarchical pipeline.",
    no_args_is_help=True,
    rich_markup_mode=None,
)


def benchmark_list(
    context: typer.Context,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    _emit(benchmark_catalog(), json_output, korean=_is_korean(context))


benchmark_commands.command("list", help="Show the comparison conditions.")(benchmark_list)
benchmark_commands.command("목록", hidden=True)(benchmark_list)


def benchmark_result(context: typer.Context, path: Annotated[Path, typer.Argument()]) -> None:
    if not path.is_file():
        typer.echo(f"결과 파일을 찾지 못했습니다: {path}" if _is_korean(context) else f"Result file not found: {path}")
        raise typer.Exit(1)
    typer.echo(path.read_text(encoding="utf-8"))


benchmark_commands.command("results", help="Show a saved JSON or Markdown result.")(benchmark_result)
benchmark_commands.command("결과", hidden=True)(benchmark_result)


def benchmark_run(
    context: typer.Context,
    url: Annotated[str, typer.Argument()],
    live: Annotated[bool, typer.Option("--live")] = False,
    repeats: Annotated[int, typer.Option("--repeats")] = 3,
    runtime: Annotated[str, typer.Option("--runtime")] = "codex",
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("benchmark-results"),
    reference: Annotated[Path | None, typer.Option("--reference")] = None,
) -> None:
    if not live:
        typer.echo(
            "외부 로그인/사용량이 발생합니다. 실행하려면 --live를 명시하세요."
            if _is_korean(context)
            else "This uses external logins and quota. Pass --live to run it."
        )
        raise typer.Exit(2)
    if reference is None or not reference.is_file():
        typer.echo(
            "공정한 채점을 위해 --reference 기준 답안 JSON 파일이 필요합니다."
            if _is_korean(context)
            else "A ground-truth JSON file is required with --reference."
        )
        raise typer.Exit(2)
    benchmark_reference = BenchmarkReference.from_json(reference.read_text(encoding="utf-8"))
    report = asyncio.run(
        BenchmarkRunner().run(
            live_benchmark_spec(
                url,
                reference=benchmark_reference,
                repeats=repeats,
                configured_runtime=runtime,
            )
        )
    )
    _, markdown_path = write_benchmark_report(report, output)
    typer.echo(markdown_path)


benchmark_commands.command("run", help="Run the explicitly enabled live comparison.")(benchmark_run)
benchmark_commands.command("실행", hidden=True)(benchmark_run)
app.add_typer(benchmark_commands, name="benchmark")
app.add_typer(benchmark_commands, name="벤치마크", hidden=True)


def normalize_cli_args(arguments: list[str]) -> list[str]:
    if arguments:
        try:
            normalize_youtube_url(arguments[0])
        except ValueError:
            if looks_like_local_media_input(arguments[0]):
                return ["summarize", *arguments]
        else:
            return ["summarize", *arguments]
    return arguments


def main() -> None:
    app(args=normalize_cli_args(sys.argv[1:]), prog_name="chew")


if __name__ == "__main__":
    main()
