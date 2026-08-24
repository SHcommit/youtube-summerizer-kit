"""Composition root for the standalone local application."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path

from chew.app.config import load_settings
from chew.app.retention import RetentionPlanner
from chew.app.service import ApplicationService
from chew.core.models import GenerationRequest, GenerationResult
from chew.harness.base import Harness, HarnessProbe
from chew.harness.registry import HarnessRegistry, default_registry
from chew.pipeline.engine import AnalysisPipeline
from chew.pipeline.outputs import OutputCompiler
from chew.storage.artifacts import ArtifactStore
from chew.storage.database import Database
from chew.telemetry import TelemetryManager
from chew.transcripts import TranscriptService, default_providers
from chew.transcripts.whisper import WhisperProvider


class AutoHarness:
    runtime_id = "auto"
    max_concurrency = 1

    def __init__(self, registry: HarnessRegistry) -> None:
        self.registry = registry
        self.preference = "auto"
        self.task_preferences: dict[str, str] = {}
        self._selected: dict[str, Harness] = {}
        self._selection_lock = asyncio.Lock()
        self._generation_limits: dict[str, asyncio.Semaphore] = {}

    def set_preference(self, runtime_id: str) -> None:
        if runtime_id != self.preference:
            self.preference = runtime_id
            self._selected.clear()
            self._generation_limits.clear()
            self.runtime_id = "auto"
            self.max_concurrency = 1

    def set_task_preferences(self, preferences: dict[str, str]) -> None:
        if preferences != self.task_preferences:
            self.task_preferences = dict(preferences)
            self._selected.clear()
            self._generation_limits.clear()

    async def _get(self, preference: str | None = None) -> Harness:
        selected_preference = preference or self.preference
        async with self._selection_lock:
            selected = self._selected.get(selected_preference)
            if selected is None:
                selected = await self.registry.select(selected_preference)
                self._selected[selected_preference] = selected
                probe = await selected.probe()
                self.runtime_id = selected.runtime_id
                self.max_concurrency = probe.capabilities.max_concurrency
                self._generation_limits[selected_preference] = asyncio.Semaphore(self.max_concurrency)
            return selected

    async def prepare(self) -> None:
        await self._get()

    async def probe(self) -> HarnessProbe:
        selected = await self._get()
        return await selected.probe()

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        preference = self.task_preferences.get(request.task, self.preference)
        selected = await self._get(preference)
        async with self._generation_limits[preference]:
            return await selected.generate(request)


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    application: ApplicationService
    telemetry: TelemetryManager


def build_container(
    *, working_directory: Path | None = None, data_directory: Path | None = None
) -> ApplicationContainer:
    data = data_directory or Path(user_data_path("youtube-summarizer-kit", appauthor=False))
    database = Database(data / "state.sqlite3")
    database.initialize()
    artifacts = ArtifactStore(data)
    settings = load_settings(working_directory or Path.cwd(), None)
    registry = default_registry(ollama_model=settings.ollama_model)
    harness = AutoHarness(registry)
    whisper = WhisperProvider()
    telemetry = TelemetryManager()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=artifacts,
        transcripts=TranscriptService(default_providers(), optional_providers=(whisper,), local_providers=(whisper,)),
        harness=harness,
        telemetry=telemetry,
    )
    application = ApplicationService(
        pipeline,
        OutputCompiler(harness, database=database, artifacts=artifacts),
        database,
        working_directory=working_directory,
        registry=registry,
        telemetry=telemetry,
    )
    return ApplicationContainer(application, telemetry)


def build_application(
    *, working_directory: Path | None = None, data_directory: Path | None = None
) -> ApplicationService:
    return build_container(working_directory=working_directory, data_directory=data_directory).application


def build_retention_planner(data_directory: Path | None = None) -> RetentionPlanner:
    data = data_directory or Path(user_data_path("youtube-summarizer-kit", appauthor=False))
    database = Database(data / "state.sqlite3")
    database.initialize()
    return RetentionPlanner(database, ArtifactStore(data))
