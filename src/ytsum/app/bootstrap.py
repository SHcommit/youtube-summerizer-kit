"""Composition root for the standalone local application."""

from __future__ import annotations

import asyncio
from pathlib import Path

from platformdirs import user_data_path

from ytsum.app.retention import RetentionPlanner
from ytsum.app.service import ApplicationService
from ytsum.core.models import GenerationRequest, GenerationResult
from ytsum.harness.base import Harness, HarnessProbe
from ytsum.harness.registry import HarnessRegistry, default_registry
from ytsum.pipeline.engine import AnalysisPipeline
from ytsum.pipeline.outputs import OutputCompiler
from ytsum.storage.artifacts import ArtifactStore
from ytsum.storage.database import Database
from ytsum.transcripts import TranscriptService, default_providers
from ytsum.transcripts.whisper import WhisperProvider


class AutoHarness:
    runtime_id = "auto"
    max_concurrency = 1

    def __init__(self, registry: HarnessRegistry) -> None:
        self.registry = registry
        self.preference = "auto"
        self._selected: Harness | None = None
        self._selection_lock = asyncio.Lock()
        self._generation_limit = asyncio.Semaphore(1)

    def set_preference(self, runtime_id: str) -> None:
        if runtime_id != self.preference:
            self.preference = runtime_id
            self._selected = None
            self.runtime_id = "auto"
            self.max_concurrency = 1

    async def _get(self) -> Harness:
        async with self._selection_lock:
            if self._selected is None:
                self._selected = await self.registry.select(self.preference)
                probe = await self._selected.probe()
                self.runtime_id = self._selected.runtime_id
                self.max_concurrency = probe.capabilities.max_concurrency
                self._generation_limit = asyncio.Semaphore(self.max_concurrency)
            return self._selected

    async def prepare(self) -> None:
        await self._get()

    async def probe(self) -> HarnessProbe:
        selected = await self._get()
        return await selected.probe()

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        selected = await self._get()
        async with self._generation_limit:
            return await selected.generate(request)


def build_application(
    *, working_directory: Path | None = None, data_directory: Path | None = None
) -> ApplicationService:
    data = data_directory or Path(user_data_path("youtube-summarizer-kit", appauthor=False))
    database = Database(data / "state.sqlite3")
    database.initialize()
    artifacts = ArtifactStore(data)
    registry = default_registry()
    harness = AutoHarness(registry)
    whisper = WhisperProvider()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=artifacts,
        transcripts=TranscriptService(
            default_providers(),
            optional_providers=(whisper,),
            local_providers=(whisper,),
        ),
        harness=harness,
    )
    return ApplicationService(
        pipeline,
        OutputCompiler(harness, database=database, artifacts=artifacts),
        database,
        working_directory=working_directory,
        registry=registry,
    )


def build_retention_planner(data_directory: Path | None = None) -> RetentionPlanner:
    data = data_directory or Path(user_data_path("youtube-summarizer-kit", appauthor=False))
    database = Database(data / "state.sqlite3")
    database.initialize()
    return RetentionPlanner(database, ArtifactStore(data))
