"""Hierarchical analysis graph and pipeline orchestration."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from chew.core.identity import fingerprint, normalize_source
from chew.core.models import (
    Chapter,
    ChapterSummary,
    ExecutionPlan,
    GenerationRequest,
    GenerationResult,
    KnowledgePack,
    MissingRange,
    SourceIdentity,
    TopicSummary,
    TopicSummaryDraft,
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
from chew.pipeline.evidence import materialize_topic_summary
from chew.pipeline.knowledge import build_knowledge_pack
from chew.pipeline.preprocessing import PreprocessingStats, TranscriptPreprocessor
from chew.pipeline.scheduler import Scheduler
from chew.pipeline.segmentation import SegmentationPolicy, SegmentManifest, segment_transcript
from chew.storage.artifacts import ArtifactCorruptError, ArtifactStore
from chew.storage.database import Database, JobRecord, JobSpec
from chew.telemetry import telemetry
from chew.transcripts.service import TranscriptService
from chew.transcripts.validation import normalize_transcript


@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    language: str
    depth: str
    instructions: str
    whisper_fallback: bool
    runtime: str
    recipe_json: str
    task_runtimes: dict[str, str] | None = None
    max_input_tokens: int | None = None
    reserved_output_tokens: int = 0
    normalize_transcript: bool = False
    preprocess_transcript: bool = False
    execution_plan: ExecutionPlan | None = None


class PipelineExecutionError(RuntimeError):
    pass


def _harness_cache_identity(harness: Harness) -> str:
    """Return a stable model selector when an adapter exposes one."""
    model = getattr(harness, "model", None)
    return model if isinstance(model, str) and model else harness.runtime_id


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
    preprocessing_stats: PreprocessingStats | None = None


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
        config: AnalysisConfig,
        *,
        transcript: Transcript | None = None,
        title: str | None = None,
        chapters: tuple[Chapter, ...] = (),
    ) -> AnalysisResult:
        source = normalize_source(url)
        if transcript is not None and transcript.source != source:
            raise ValueError("provided transcript source does not match analysis URL")
        request_key = fingerprint(
            {
                "segmentation": 1,
                "prompt": PROMPT_FINGERPRINT,
                "runtime": config.runtime,
                "task_runtimes": config.task_runtimes or {},
                "execution_plan": (
                    config.execution_plan.model_dump(mode="json") if config.execution_plan is not None else None
                ),
                "model": _harness_cache_identity(self.harness),
                "depth": config.depth,
                "language": config.language,
                "instructions": config.instructions,
                "preprocessing": {
                    "normalize_transcript": config.normalize_transcript,
                    "preprocess_transcript": config.preprocess_transcript,
                    "recipe": 1,
                },
                "schema": 1,
                "provided_transcript": fingerprint(transcript) if transcript is not None else None,
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

        cached_hash = None if transcript is not None else self.database.get_cached_transcript(source.source_id, config.language)
        if cached_hash is not None:
            try:
                transcript = Transcript.model_validate(
                    self.artifacts.get_json(self.artifacts.ref_for_digest(cached_hash))
                )
            except (ArtifactCorruptError, ValidationError):
                cached_hash = None
        if transcript is not None:
            self.artifacts.put_json(transcript)
        elif cached_hash is None:
            with telemetry.span("chew.transcript_acquisition", {"source": source.canonical_url or source.source_id}):
                resolution = await self.transcripts.resolve(
                    source,
                    config.language,
                    include_optional=config.whisper_fallback,
                )
                transcript = resolution.transcript
                transcript_ref = self.artifacts.put_json(transcript)
                self.database.cache_transcript(
                    source.source_id,
                    config.language,
                    transcript_ref.digest,
                    fingerprint(transcript),
                )
        assert transcript is not None
        raw_transcript_hash = fingerprint(transcript)
        analysis_transcript = normalize_transcript(transcript) if config.normalize_transcript else transcript
        preprocessing_stats: PreprocessingStats | None = None
        detector = None
        if config.preprocess_transcript:
            preprocessor = TranscriptPreprocessor()
            analysis_transcript, preprocessing_stats = preprocessor.process(analysis_transcript)
            detector = preprocessor.boundary_detector
        if analysis_transcript is not transcript:
            self.artifacts.put_json(analysis_transcript)
        transcript_hash = fingerprint(analysis_transcript)
        selected_chapters = chapters or transcript.chapters
        with telemetry.span(
            "chew.segmentation",
            {
                "raw_chapters": len(transcript.chapters),
                "selected_chapters": len(selected_chapters),
                "depth": config.depth,
            },
        ):
            manifest = segment_transcript(
                analysis_transcript,
                selected_chapters,
                SegmentationPolicy(
                    max_input_tokens=config.max_input_tokens,
                    reserved_output_tokens=config.reserved_output_tokens,
                ),
                detector=detector,
                depth=config.depth,
            )
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
                    recipe_json=config.recipe_json,
                    source_locator=source.local_path or source.canonical_url,
                    execution_plan_json=(
                        config.execution_plan.model_dump_json() if config.execution_plan is not None else ""
                    ),
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
                    "language": config.language,
                    "user_instructions": config.instructions,
                    "segments": [
                        {
                            **analysis_transcript.segments[index].model_dump(mode="json"),
                            "segment_index": index,
                        }
                        for index in topic.segment_indexes
                    ],
                    "raw_segment_indexes": list(topic.segment_indexes),
                }
            elif job.kind == "chapter":
                chapter_id = job.job_id.split(":chapter:", 1)[1]
                chapter = chapter_by_id[chapter_id]
                payload = {
                    "chapter_id": chapter.chapter_id,
                    "title": chapter.title,
                    "language": config.language,
                    "user_instructions": config.instructions,
                }
            else:
                payload = {
                    "source": source.model_dump(mode="json"),
                    "title": title or transcript.title or "YouTube 영상",
                    "language": config.language,
                    "user_instructions": config.instructions,
                    "transcript_fingerprint": raw_transcript_hash,
                    "topic_ranges": {
                        topic.topic_id: {"start_ms": topic.start_ms, "end_ms": topic.end_ms}
                        for topic in manifest.topics
                    },
                }
            payload_ref = self.artifacts.put_json(payload)
            self.database.upsert_job(replace(job, payload_hash=payload_ref.digest))

        handler = _AnalysisJobHandler(
            self.database,
            self.artifacts,
            self.harness,
            raw_transcript=transcript,
            raw_transcript_fingerprint=raw_transcript_hash,
            execution_plan=config.execution_plan,
        )
        scheduler = Scheduler(
            self.database,
            handler,
            global_concurrency=self.concurrency,
            runtime_limits={self.harness.runtime_id: self.concurrency},
        )
        with telemetry.span(
            "chew.dag_scheduler",
            {
                "total_jobs": len(graph),
                "concurrency": self.concurrency,
                "runtime": self.harness.runtime_id,
            },
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
            run_id,
            pack,
            False,
            dict(handler.usage),
            tuple(sorted(handler.models)),
            preprocessing_stats,
        )


class _AnalysisJobHandler:
    def __init__(
        self,
        database: Database,
        artifacts: ArtifactStore,
        harness: Harness,
        *,
        raw_transcript: Transcript,
        raw_transcript_fingerprint: str,
        execution_plan: ExecutionPlan | None,
    ) -> None:
        self.database = database
        self.artifacts = artifacts
        self.harness = harness
        self.raw_transcript = raw_transcript
        self.raw_transcript_fingerprint = raw_transcript_fingerprint
        self.execution_plan = execution_plan
        self.usage: dict[str, int] = {}
        self.models: set[str] = set()

    def _record_result(self, job: JobRecord, request: GenerationRequest, result: object) -> None:
        generated = GenerationResult.model_validate(result)
        encoded_input = json.dumps(request.input, ensure_ascii=False, separators=(",", ":"))
        encoded_schema = json.dumps(request.output_schema, ensure_ascii=False, separators=(",", ":"))
        segments = request.input.get("segments")
        self.database.record_job_measurement(
            job_id=job.job_id,
            request_id=generated.request_id,
            task=request.task,
            runtime_id=generated.runtime_id,
            model=generated.model,
            usage=generated.usage,
            details={
                "input_chars": len(encoded_input),
                "input_segment_count": len(segments) if isinstance(segments, list) else 0,
                "output_schema_chars": len(encoded_schema),
                "is_repair": request.task == "repair",
                "retry": job.attempts > 1,
                "policy_fingerprint": (
                    self.execution_plan.plan_fingerprint if self.execution_plan is not None else ""
                ),
            },
        )
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
                "properties": {
                    "overview": {"type": "string"},
                    "further_study": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["overview", "further_study"],
                "additionalProperties": False,
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
        self._record_result(job, request, result)
        try:
            return self._validate_output(result.output, model)
        except (ValidationError, ValueError):
            repair_request = GenerationRequest(
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
            repair = await self.harness.generate(
                repair_request
            )
            self._record_result(job, repair_request, repair)
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
            output = await self._generate(job, "topic_summary", TOPIC_PROMPT, payload, TopicSummaryDraft)
            topic, evidence_stats = materialize_topic_summary(
                TopicSummaryDraft.model_validate(output),
                transcript=self.raw_transcript,
                raw_transcript_fingerprint=self.raw_transcript_fingerprint,
                allowed_segment_indexes=tuple(int(index) for index in payload["raw_segment_indexes"]),
            )
            if evidence_stats.candidate_count:
                self.database.record_job_measurement(
                    job_id=job.job_id,
                    request_id=f"{job.job_id}:evidence-validation",
                    task="evidence_validation",
                    runtime_id="validator",
                    model=None,
                    usage={},
                    details={
                        "candidate_count": evidence_stats.candidate_count,
                        "valid_count": evidence_stats.valid_count,
                        "invalid_count": evidence_stats.invalid_count,
                        "policy_fingerprint": (
                            self.execution_plan.plan_fingerprint if self.execution_plan is not None else ""
                        ),
                    },
                )
            return self.artifacts.put_json(topic).digest
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
            failed_topic_ids=tuple(
                job_id.split(":topic:", 1)[1]
                for job_id in self.database.failed_job_ids(job.run_id, "topic")
            ),
            missing_ranges=tuple(
                MissingRange.model_validate(payload["topic_ranges"][topic_id])
                for topic_id in (
                    job_id.split(":topic:", 1)[1]
                    for job_id in self.database.failed_job_ids(job.run_id, "topic")
                )
            ),
            runtime_id=self.harness.runtime_id,
            model=next(iter(self.models)) if len(self.models) == 1 else None,
        )
        ref = self.artifacts.put_json(pack)
        self.database.set_run_pack(job.run_id, ref.digest)
        return ref.digest
