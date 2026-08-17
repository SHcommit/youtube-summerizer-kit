"""Application facade shared by the human CLI and future integrations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chew.app.config import Settings, load_settings
from chew.harness.builtin import HarnessAuthenticationError
from chew.harness.registry import HarnessRegistry
from chew.pipeline.engine import AnalysisPipeline
from chew.pipeline.outputs import OutputCompiler
from chew.storage.database import Database


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
    ) -> None:
        self.pipeline = pipeline
        self.compiler = compiler
        self.database = database
        self.working_directory = working_directory or Path.cwd()
        self.registry = registry

    async def generate(
        self, url: str, profile: str, destination: Path, depth: str | None = None
    ) -> CommandResult:
        analysis_settings = load_settings(self.working_directory, None)
        if depth:
            analysis_settings = analysis_settings.model_copy(update={"depth": depth})
        output_settings = load_settings(self.working_directory, profile)
        if depth:
            output_settings = output_settings.model_copy(update={"depth": depth})
        return await self._generate(url, profile, destination, analysis_settings, output_settings)

    async def _generate(
        self,
        url: str,
        profile: str,
        destination: Path,
        analysis_settings: Settings,
        output_settings: Settings,
    ) -> CommandResult:
        preference = getattr(self.pipeline.harness, "set_preference", None)
        if callable(preference):
            preference(analysis_settings.runtime)
        try:
            result = await self.pipeline.analyze(url, analysis_settings)
            output = await self.compiler.compile(result.pack, profile, output_settings, destination)
        except HarnessAuthenticationError as error:
            raise AuthenticationRequired(error.runtime_id, error.login_command) from error
        for path in output.files:
            self.database.register_export(result.run_id, path)
        return CommandResult(result.run_id, profile, result.reused, output.files)

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
