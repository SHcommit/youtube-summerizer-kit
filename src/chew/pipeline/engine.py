"""Hierarchical analysis graph and pipeline orchestration."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from chew.app.config import Settings
from chew.core.identity import fingerprint, normalize_source
from chew.core.models import (
    Chapter,
    ChapterSummary,
    GenerationRequest,
    GenerationResult,
    KnowledgePack,
    SourceIdentity,
    TopicSummary,
    Transcript,
)
from chew.core.prompts import (
    CHAPTER_PROMPT,
    COMPOSE_PROMPT,
    PROMPT_FINGERPRINT,
    REPAIR_PROMPT,
    TOPIC_PROMPT,
)
from chew.harness.base import Harness
from chew.pipeline.knowledge import build_knowledge_pack
from chew.pipeline.scheduler import Scheduler
from chew.pipeline.segmentation import SegmentationPolicy, SegmentManifest, segment_transcript
from chew.storage.artifacts import ArtifactCorruptError, ArtifactStore
from chew.storage.database import Database, JobRecord, JobSpec
from chew.telemetry import telemetry
from chew.transcripts.service import TranscriptService


class PipelineExecutionError(RuntimeError):
    pass


def build_analysis_job_graph(
    run_id: str,
    manifest: SegmentManifest,
    runtime_id: str,
) -> tuple[JobSpec, ...]:
    jobs: list[JobSpec] = []
    topic_job_ids: dict[str, list[str]] = {}
    for topic in manifest.topics:
        job_id = f"{run_id}:topic:{topic.topic_id}"
        jobs.append(JobSpec(job_id, run_id, "topic", 20, runtime_id=runtime_id))
        topic_job_ids.setdefault(topic.chapter_id, []).append(job_id)

    chapter_job_ids: list[str] = []
    for chapter in manifest.chapters:
        job_id = f"{run_id}:chapter:{chapter.chapter_id}"
        chapter_job_ids.append(job_id)
        jobs.append(
            JobSpec(
                job_id,
                run_id,
                "chapter",
                10,
                tuple(topic_job_ids.get(chapter.chapter_id, ())),
                runtime_id,
            )
        )
    jobs.append(
        JobSpec(
            f"{run_id}:compose",
            run_id,
            "compose",
            5,
            tuple(chapter_job_ids),
            runtime_id,
        )
    )
    return tuple(jobs)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    run_id: str
    pack: KnowledgePack
    reused: bool
    usage: dict[str, int] | None = None
    models: tuple[str, ...] = ()


class AnalysisPipeline:
    def __init__(
        self,
        *,
        database: Database,
        artifacts: ArtifactStore,
        transcripts: TranscriptService,
        harness: Harness,
        concurrency: int = 2,
    ) -> None:
        self.database = database
        self.artifacts = artifacts
        self.transcripts = transcripts
        self.harness = harness
        self.concurrency = concurrency

    async def analyze(
        self,
        url: str,
        settings: Settings,
        *,
        title: str | None = None,
        chapters: tuple[Chapter, ...] = (),
    ) -> AnalysisResult:
        source = normalize_source(url)
        request_key = fingerprint(
            {
                "segmentation": 1,
                "prompt": PROMPT_FINGERPRINT,
                "runtime": settings.runtime,
                "depth": settings.depth,
                "language": settings.language,
                "instructions": settings.instructions,
                "schema": 1,
            }
        )
        reusable = self.database.find_reusable_run(source.source_id, request_key)
        if reusable is not None:
            pack_hash = self.database.get_run_pack(reusable)
            if pack_hash is not None:
                pack = KnowledgePack.model_validate(
                    self.artifacts.get_json(self.artifacts.ref_for_digest(pack_hash))
                )
                return AnalysisResult(reusable, pack, True)

        cached_hash = self.database.get_cached_transcript(source.source_id, settings.language)
        if cached_hash is not None:
            try:
                transcript = Transcript.model_validate(
                    self.artifacts.get_json(self.artifacts.ref_for_digest(cached_hash))
                )
            except (ArtifactCorruptError, ValidationError):
                cached_hash = None
        if cached_hash is None:
            with telemetry.span("chew.transcript_acquisition", {"source": source.canonical_url or source.source_id}):
                resolution = await self.transcripts.resolve(
                    source,
                    settings.language,
                    include_optional=settings.whisper_fallback,
                )
                transcript = resolution.transcript
                transcript_ref = self.artifacts.put_json(transcript)
                self.database.cache_transcript(
                    source.source_id,
                    settings.language,
                    transcript_ref.digest,
                    fingerprint(transcript),
                )
        transcript_hash = fingerprint(transcript)
        selected_chapters = chapters or transcript.chapters
        with telemetry.span(
            "chew.segmentation",
            {"raw_chapters": len(transcript.chapters), "selected_chapters": len(selected_chapters)},
        ):
            manifest = segment_transcript(transcript, selected_chapters, SegmentationPolicy())
        analysis_key = fingerprint(
            {
                "transcript": transcript_hash,
                "request": request_key,
            }
        )
        compatible = self.database.find_compatible_run(source.source_id, analysis_key)
        if compatible is not None:
            pack_hash = self.database.get_run_pack(compatible)
            if pack_hash is not None:
                pack = KnowledgePack.model_validate(
                    self.artifacts.get_json(self.artifacts.ref_for_digest(pack_hash))
                )
                return AnalysisResult(compatible, pack, True)
            run_id = compatible
        else:
            run_id = str(uuid4())
            try:
                self.database.create_run(
                    run_id,
                    source.source_id,
                    analysis_key,
                    request_key=request_key,
                    recipe_json=settings.model_dump_json(),
                    source_locator=source.local_path or source.canonical_url,
                )
            except sqlite3.IntegrityError:
                winner = self.database.find_compatible_run(source.source_id, analysis_key)
                if winner is None:
                    raise
                run_id = winner

        graph = build_analysis_job_graph(run_id, manifest, self.harness.runtime_id)
        topic_by_id = {topic.topic_id: topic for topic in manifest.topics}
        chapter_by_id = {chapter.chapter_id: chapter for chapter in manifest.chapters}
        for job in graph:
            payload: dict[str, Any]
            if job.kind == "topic":
                topic_id = job.job_id.split(":topic:", 1)[1]
                topic = topic_by_id[topic_id]
                payload = {
                    "topic_id": topic.topic_id,
                    "title": topic.title,
                    "language": settings.language,
                    "user_instructions": settings.instructions,
                    "segments": [
                        transcript.segments[index].model_dump(mode="json")
                        for index in topic.segment_indexes
                    ],
                }
            elif job.kind == "chapter":
                chapter_id = job.job_id.split(":chapter:", 1)[1]
                chapter = chapter_by_id[chapter_id]
                payload = {
                    "chapter_id": chapter.chapter_id,
                    "title": chapter.title,
                    "language": settings.language,
                    "user_instructions": settings.instructions,
                }
            else:
                payload = {
                    "source": source.model_dump(mode="json"),
                    "title": title or transcript.title or "YouTube 영상",
                    "language": settings.language,
                    "user_instructions": settings.instructions,
                    "transcript_fingerprint": transcript_hash,
                }
            payload_ref = self.artifacts.put_json(payload)
            self.database.upsert_job(replace(job, payload_hash=payload_ref.digest))

        handler = _AnalysisJobHandler(self.database, self.artifacts, self.harness)
        scheduler = Scheduler(
            self.database,
            handler,
            global_concurrency=self.concurrency,
            runtime_limits={self.harness.runtime_id: self.concurrency},
        )
        with telemetry.span(
            "chew.dag_scheduler",
            {"total_jobs": len(graph), "concurrency": self.concurrency, "runtime": self.harness.runtime_id},
        ):
            summary = await scheduler.run(run_id)
        pack_hash = self.database.get_run_pack(run_id)
        if pack_hash is None:
            raise PipelineExecutionError(
                f"Knowledge Pack 생성 실패: {summary.failed_jobs}개 작업 실패"
            )
        pack = KnowledgePack.model_validate(
            self.artifacts.get_json(self.artifacts.ref_for_digest(pack_hash))
        )
        return AnalysisResult(
            run_id, pack, False, dict(handler.usage), tuple(sorted(handler.models))
        )


class _AnalysisJobHandler:
    def __init__(self, database: Database, artifacts: ArtifactStore, harness: Harness) -> None:
        self.database = database
        self.artifacts = artifacts
        self.harness = harness
        self.usage: dict[str, int] = {}
        self.models: set[str] = set()

    def _record_result(self, result: object) -> None:
        generated = GenerationResult.model_validate(result)
        for key, value in generated.usage.items():
            self.usage[key] = self.usage.get(key, 0) + value
        if generated.model:
            self.models.add(generated.model)

    def _load(self, digest: str) -> dict[str, Any]:
        return self.artifacts.get_json(self.artifacts.ref_for_digest(digest))

    async def _generate(
        self,
        job: JobRecord,
        task: str,
        instruction: str,
        input_value: dict[str, Any],
        model: type[BaseModel] | None,
    ) -> dict[str, Any]:
        schema = (
            model.model_json_schema()
            if model is not None
            else {
                "type": "object",
                "required": ["overview", "further_study"],
            }
        )
        request = GenerationRequest(
            request_id=job.job_id,
            task=task,
            input={**input_value, "instruction": instruction},
            output_schema=schema,
            trace_id=job.run_id,
        )
        result = await self.harness.generate(request)
        self._record_result(result)
        try:
            return self._validate_output(result.output, model)
        except (ValidationError, ValueError):
            repair = await self.harness.generate(
                GenerationRequest(
                    request_id=f"{job.job_id}:repair",
                    task="repair",
                    input={
                        "instruction": REPAIR_PROMPT,
                        "target_task": task,
                        "original_input": input_value,
                        "invalid_output": result.output,
                    },
                    output_schema=schema,
                    trace_id=job.run_id,
                )
            )
            self._record_result(repair)
            return self._validate_output(repair.output, model)

    @staticmethod
    def _validate_output(output: dict[str, Any], model: type[BaseModel] | None) -> dict[str, Any]:
        if model is not None:
            return model.model_validate(output).model_dump(mode="json")
        overview = output.get("overview") or output.get("summary") or output.get("description")
        if not isinstance(overview, str):
            overview = str(output.get("text") or output)
        output["overview"] = overview
        further_study = output.get("further_study")
        if not isinstance(further_study, list):
            further_study = []
        output["further_study"] = [str(item) for item in further_study]
        return output

    async def handle(self, job: JobRecord) -> str:
        payload = self._load(job.payload_hash)
        if job.kind == "topic":
            output = await self._generate(job, "topic_summary", TOPIC_PROMPT, payload, TopicSummary)
            return self.artifacts.put_json(output).digest
        if job.kind == "chapter":
            topic_payloads = [
                self._load(digest) for digest in self.database.dependency_results(job.job_id)
            ]
            payload["topics"] = topic_payloads
            payload["topic_ids"] = [str(topic["topic_id"]) for topic in topic_payloads]
            output = await self._generate(
                job, "chapter_summary", CHAPTER_PROMPT, payload, ChapterSummary
            )
            return self.artifacts.put_json(output).digest

        chapters = [
            ChapterSummary.model_validate(self._load(digest))
            for digest in self.database.results_by_kind(job.run_id, "chapter")
        ]
        topic_models = [
            TopicSummary.model_validate(self._load(digest))
            for digest in self.database.results_by_kind(job.run_id, "topic")
        ]
        payload["chapters"] = [chapter.model_dump(mode="json") for chapter in chapters]
        composition = await self._generate(job, "compose", COMPOSE_PROMPT, payload, None)
        pack = build_knowledge_pack(
            source=SourceIdentity.model_validate(payload["source"]),
            title=str(payload["title"]),
            language=str(payload["language"]),
            overview=str(composition["overview"]),
            transcript_fingerprint=str(payload["transcript_fingerprint"]),
            topics=tuple(topic_models),
            chapters=tuple(chapters),
            further_study=tuple(str(value) for value in composition["further_study"]),
        )
        ref = self.artifacts.put_json(pack)
        self.database.set_run_pack(job.run_id, ref.digest)
        return ref.digest
