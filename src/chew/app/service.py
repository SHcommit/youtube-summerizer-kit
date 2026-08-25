"""Application facade shared by the human CLI and future integrations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chew.app.config import Settings, load_settings
from chew.core.identity import normalize_source
from chew.core.models import Transcript
from chew.harness.base import ConfigurableHarness
from chew.harness.builtin import HarnessAuthenticationError
from chew.harness.registry import HarnessRegistry
from chew.pipeline.engine import AnalysisConfig, AnalysisPipeline
from chew.pipeline.outputs import OutputCompiler
from chew.pipeline.policy import LOCAL_RUNTIME_IDS, build_execution_plan
from chew.pipeline.preprocessing import PreprocessingStats
from chew.storage.database import Database
from chew.telemetry import TelemetryManager
from chew.transcripts.user_input import UserTranscriptProvider


class AuthenticationRequired(RuntimeError):
    def __init__(self, runtime_id: str, login_command: str) -> None:
        self.runtime_id = runtime_id
        self.login_command = login_command
        super().__init__(f"Authentication required for {runtime_id}. Run: {login_command}")


@dataclass(frozen=True, slots=True)
class CommandResult:
    run_id: str
    profile: str
    reused: bool
    files: tuple[Path, ...]
    usage: dict[str, int] | None = None
    preprocessing_stats: PreprocessingStats | None = None


@dataclass(frozen=True, slots=True)
class RunStatus:
    run_id: str
    source_id: str
    status: str
    completed_jobs: int
    total_jobs: int


class ApplicationService:
    def __init__(
        self,
        pipeline: AnalysisPipeline,
        compiler: OutputCompiler,
        database: Database,
        *,
        working_directory: Path | None = None,
        registry: HarnessRegistry | None = None,
        telemetry: TelemetryManager | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.compiler = compiler
        self.database = database
        self.working_directory = working_directory or Path.cwd()
        self.registry = registry
        self.telemetry = telemetry

    async def generate(
        self,
        url: str,
        profile: str,
        destination: Path,
        depth: str | None = None,
        transcript_path: Path | None = None,
    ) -> CommandResult:
        analysis_settings = load_settings(self.working_directory, None)
        if depth:
            analysis_settings = analysis_settings.model_copy(update={"depth": depth})
        output_settings = load_settings(self.working_directory, profile)
        if depth:
            output_settings = output_settings.model_copy(update={"depth": depth})
        transcript: Transcript | None = None
        if transcript_path is not None:
            source = normalize_source(url)
            transcript = await UserTranscriptProvider(transcript_path).fetch(source, analysis_settings.language)
        return await self._generate(url, profile, destination, analysis_settings, output_settings, transcript=transcript)

    async def _generate(
        self,
        url: str,
        profile: str,
        destination: Path,
        analysis_settings: Settings,
        output_settings: Settings,
        *,
        transcript: Transcript | None = None,
    ) -> CommandResult:
        if self.telemetry is None:
            return await self._generate_in_scope(
                url, profile, destination, analysis_settings, output_settings, transcript=transcript
            )
        with self.telemetry.run():
            return await self._generate_in_scope(
                url, profile, destination, analysis_settings, output_settings, transcript=transcript
            )

    async def _generate_in_scope(
        self,
        url: str,
        profile: str,
        destination: Path,
        analysis_settings: Settings,
        output_settings: Settings,
        *,
        transcript: Transcript | None = None,
    ) -> CommandResult:
        local_requested = analysis_settings.local_accelerator or any(
            runtime_id in LOCAL_RUNTIME_IDS for runtime_id in analysis_settings.task_runtimes.values()
        )
        requested_task_runtimes = dict(analysis_settings.task_runtimes)
        if local_requested:
            requested_task_runtimes.setdefault("transcript_annotate", "ollama")
        plan = build_execution_plan(
            frontier_runtime_id=analysis_settings.runtime,
            requested_task_runtimes=requested_task_runtimes,
            local_accelerator_requested=local_requested,
            local_accelerator_available=await self._local_accelerator_available(local_requested),
            max_input_tokens=analysis_settings.max_input_tokens,
            reserved_output_tokens=analysis_settings.reserved_output_tokens,
        )
        if isinstance(self.pipeline.harness, ConfigurableHarness):
            self.pipeline.harness.set_preference(plan.default_runtime_id)
        set_task_preferences = getattr(self.pipeline.harness, "set_task_preferences", None)
        if callable(set_task_preferences):
            set_task_preferences({route.task: route.runtime_id for route in plan.task_routes})
        config = AnalysisConfig(
            language=analysis_settings.language,
            depth=analysis_settings.depth,
            instructions=analysis_settings.instructions,
            whisper_fallback=analysis_settings.whisper_fallback,
            runtime=plan.default_runtime_id,
            recipe_json=analysis_settings.model_dump_json(),
            task_runtimes={route.task: route.runtime_id for route in plan.task_routes},
            max_input_tokens=plan.max_input_tokens,
            reserved_output_tokens=plan.reserved_output_tokens,
            normalize_transcript=analysis_settings.normalize_transcript,
            preprocess_transcript=analysis_settings.preprocess_transcript,
            execution_plan=plan,
            compiler_strategy="gkt",
        )
        try:
            if transcript is None:
                result = await self.pipeline.analyze(url, config)
            else:
                result = await self.pipeline.analyze(url, config, transcript=transcript)
            output = await self.compiler.compile(result.pack, profile, output_settings, destination)
        except HarnessAuthenticationError as error:
            raise AuthenticationRequired(error.runtime_id, error.login_command) from error
        for path in output.files:
            self.database.register_export(result.run_id, path)
        return CommandResult(
            result.run_id,
            profile,
            result.reused,
            output.files,
            result.usage,
            result.preprocessing_stats,
        )

    async def _local_accelerator_available(self, requested: bool) -> bool | None:
        if not requested or self.registry is None:
            return None
        try:
            harness = await self.registry.select("ollama")
            probe = await harness.probe()
        except (HarnessAuthenticationError, RuntimeError):
            return False
        return probe.available and probe.auth_ready is not False

    def status(self, run_id: str | None = None) -> tuple[RunStatus, ...]:
        return tuple(RunStatus(*row) for row in self.database.list_run_statuses(run_id))

    async def resume(self, run_id: str | None = None) -> CommandResult:
        selected = self.database.get_resumable_run(run_id)
        if selected is None:
            raise LookupError("No resumable analysis was found.")
        selected_id, source_id = selected
        stored_recipe = self.database.get_run_recipe(selected_id)
        analysis_settings = (
            load_settings(self.working_directory, None)
            if stored_recipe is None
            else Settings.model_validate_json(stored_recipe)
        )
        output_settings = load_settings(self.working_directory, "digest")
        self.database.prepare_resume(selected_id)
        source_locator = self.database.get_run_source_locator(selected_id)
        if source_locator is None:
            video_id = source_id.removeprefix("youtube:")
            source_locator = f"https://www.youtube.com/watch?v={video_id}"
        return await self._generate(
            source_locator,
            "digest",
            self.working_directory / "chew-output" / selected_id,
            analysis_settings,
            output_settings,
        )

    def diagnostics(self) -> dict[str, object]:
        if self.registry is not None:
            import asyncio

            probes = asyncio.run(self.registry.probe_all())
            return {"runtimes": [probe.model_dump(mode="json") for probe in probes]}
        probe = getattr(self.pipeline.harness, "probe", None)
        return {"runtime": self.pipeline.harness.runtime_id, "probe_supported": callable(probe)}
