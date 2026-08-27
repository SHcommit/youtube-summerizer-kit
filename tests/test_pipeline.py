from pathlib import Path

import pytest

from chew.domain import (
    Chapter,
    GenerationRequest,
    GenerationResult,
    Provenance,
    RunManifest,
    SourceIdentity,
    SourceKind,
    Transcript,
    TranscriptSegment,
)
from chew.harness.base import ExternalOutcomeUnknown
from chew.identity import normalize_source
from chew.pipeline import AnalysisPipeline, build_analysis_job_graph
from chew.pipeline.engine import AnalysisConfig, PipelineExecutionError
from chew.pipeline.policy import build_execution_plan
from chew.segmentation import SegmentationPolicy, segment_transcript
from chew.storage.artifacts import ArtifactStore
from chew.storage.database import Database
from chew.telemetry import TelemetryManager
from chew.transcripts.service import TranscriptResolution, TranscriptService


def test_analysis_config_is_defined() -> None:
    config = AnalysisConfig(
        language="ko",
        depth="detailed",
        instructions="",
        whisper_fallback=False,
        runtime="auto",
        recipe_json='{"language":"ko"}',
    )
    assert config.language == "ko"
    assert config.depth == "detailed"
    assert config.recipe_json == '{"language":"ko"}'
    assert config.max_input_tokens is None
    assert config.normalize_transcript is False
    assert config.preprocess_transcript is False


def test_analysis_graph_has_topic_chapter_and_final_dependencies() -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="ko",
        duration_ms=12 * 60_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=tuple(
            TranscriptSegment(
                start_ms=index * 60_000,
                end_ms=(index + 1) * 60_000,
                text=f"segment {index}",
            )
            for index in range(12)
        ),
    )
    chapters = (
        Chapter(chapter_id="intro", title="소개", start_ms=0, end_ms=6 * 60_000),
        Chapter(
            chapter_id="core",
            title="핵심",
            start_ms=6 * 60_000,
            end_ms=12 * 60_000,
        ),
    )
    manifest = segment_transcript(transcript, chapters, SegmentationPolicy())

    graph = build_analysis_job_graph("run-1", manifest, "fake")

    topics = [job for job in graph if job.kind == "topic"]
    reducers = [job for job in graph if job.kind == "chapter"]
    final = next(job for job in graph if job.kind == "compose")
    assert len(topics) == 2
    assert {job.job_id for job in reducers} == {"run-1:chapter:intro", "run-1:chapter:core"}
    assert set(final.dependencies) == {job.job_id for job in reducers}


class StaticTranscriptProvider:
    name = "fixture"

    def __init__(self, transcript: Transcript) -> None:
        self.transcript = transcript
        self.calls = 0

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript:
        self.calls += 1
        return self.transcript.model_copy(update={"source": source, "language": language})


class StructuredFakeHarness:
    runtime_id = "fake"

    def __init__(self, break_first_topic: bool = False) -> None:
        self.calls: list[str] = []
        self.requests: list[GenerationRequest] = []
        self.break_first_topic = break_first_topic
        self.broken = False

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.calls.append(request.task)
        self.requests.append(request)
        if request.task == "topic_summary":
            if self.break_first_topic and not self.broken:
                self.broken = True
                output = {"invalid": True}
            else:
                output = self.topic_output(request.input)
        elif request.task == "repair":
            output = self.topic_output(request.input["original_input"])
        elif request.task == "chapter_summary":
            output = {
                "chapter_id": request.input["chapter_id"],
                "title": request.input["title"],
                "summary": "챕터 요약",
                "topic_ids": request.input["topic_ids"],
            }
        else:
            output = {"overview": "전체 요약", "further_study": ["추가 개념"]}
        return GenerationResult(
            request_id=request.request_id,
            output=output,
            runtime_id=self.runtime_id,
            model="fake-model",
        )

    @staticmethod
    def topic_output(input_value: dict[str, object]) -> dict[str, object]:
        return {
            "topic_id": input_value["topic_id"],
            "title": input_value["title"],
            "summary": "소주제 요약",
            "claims": [],
            "concepts": ["개념"],
            "examples": [],
        }


class PartiallyFailingHarness(StructuredFakeHarness):
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.task == "topic_summary" and request.input["topic_id"] == "full-video-topic-001":
            raise RuntimeError("fixture topic failure")
        return await super().generate(request)


class EvidenceCandidateHarness(StructuredFakeHarness):
    @staticmethod
    def topic_output(input_value: dict[str, object]) -> dict[str, object]:
        segment = input_value["segments"][0]
        assert isinstance(segment, dict)
        return {
            "topic_id": input_value["topic_id"],
            "title": input_value["title"],
            "summary": "소주제 요약",
            "claims": [
                {
                    "text": "응답 시간이 감소했다.",
                    "provenance": "source",
                    "evidence_candidates": [
                        {
                            "segment_indexes": [segment["segment_index"]],
                            "start_ms": segment["start_ms"],
                            "end_ms": segment["end_ms"],
                            "quote": segment["text"],
                        }
                    ],
                }
            ],
            "concepts": [],
            "examples": [],
        }


class GroundedTreeHarness:
    runtime_id = "fake"

    def __init__(self) -> None:
        self.requests: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)
        if request.task == "transcript_annotate":
            return GenerationResult(
                request_id=request.request_id,
                runtime_id="ollama",
                model="local-model",
                output={"annotations": []},
            )
        return GenerationResult(
            request_id=request.request_id,
            runtime_id=self.runtime_id,
            model="fake-model",
            output={
                "thesis_claim_id": "claim-1",
                "claims": [
                    {
                        "claim_id": "claim-1",
                        "text": "The transcript is grounded.",
                        "occurrence_ids": ["occurrence-1"],
                    }
                ],
                "occurrences": [
                    {
                        "occurrence_id": "occurrence-1",
                        "raw_segment_indexes": [0],
                        "quote": "The transcript is grounded.",
                    }
                ],
            },
        )


class UnknownOutcomeHarness(GroundedTreeHarness):
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)
        raise ExternalOutcomeUnknown("provider acceptance could not be determined")


@pytest.mark.asyncio
async def test_gkt_pipeline_uses_one_extraction_without_hierarchical_jobs(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=10_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=10_000, text="The transcript is grounded."),),
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    harness = GroundedTreeHarness()
    telemetry = TelemetryManager()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path),
        transcripts=TranscriptService([StaticTranscriptProvider(transcript)]),
        harness=harness,
        telemetry=telemetry,
    )

    result = await pipeline.analyze(
        source.canonical_url,
        AnalysisConfig(
            language="en",
            depth="detailed",
            instructions="",
            whisper_fallback=False,
            runtime="fake",
            recipe_json="{}",
            compiler_strategy="gkt",
        ),
    )

    assert [request.task for request in harness.requests] == ["knowledge_extract"]
    assert result.pack.grounded_tree_fingerprint
    assert database.list_run_statuses(result.run_id)[0][4] == 0
    assert [checkpoint[0] for checkpoint in database.list_compiler_checkpoints(result.run_id)] == [
        "input.compile",
        "frontier.generate",
        "evidence.ground",
        "tree.assemble",
    ]
    assert {span.name for span in telemetry.spans} >= {
        "input.compile",
        "frontier.generate",
        "evidence.ground",
        "tree.assemble",
    }


@pytest.mark.asyncio
async def test_gkt_pipeline_persists_run_manifest_linked_to_pack(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=10_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=10_000, text="The transcript is grounded."),),
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    artifacts = ArtifactStore(tmp_path)
    harness = GroundedTreeHarness()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=artifacts,
        transcripts=TranscriptService([StaticTranscriptProvider(transcript)]),
        harness=harness,
        telemetry=TelemetryManager(),
    )

    result = await pipeline.analyze(
        source.canonical_url,
        AnalysisConfig(
            language="en",
            depth="detailed",
            instructions="",
            whisper_fallback=False,
            runtime="fake",
            recipe_json="{}",
            compiler_strategy="gkt",
        ),
    )

    assert result.pack.manifest_hash is not None
    assert database.get_run_manifest(result.run_id) == result.pack.manifest_hash
    manifest = RunManifest.model_validate(
        artifacts.get_json(artifacts.ref_for_digest(result.pack.manifest_hash))
    )
    assert manifest.run_id == result.run_id
    assert manifest.compiler.strategy == "gkt"
    assert manifest.inputs.raw_transcript_fingerprint == result.pack.transcript_fingerprint


@pytest.mark.asyncio
async def test_gkt_pipeline_marks_uncertain_provider_request_without_retrying(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=10_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=10_000, text="The transcript is grounded."),),
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    harness = UnknownOutcomeHarness()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path),
        transcripts=TranscriptService([StaticTranscriptProvider(transcript)]),
        harness=harness,
    )

    with pytest.raises(PipelineExecutionError, match="outcome is unknown"):
        await pipeline.analyze(
            source.canonical_url,
            AnalysisConfig(
                language="en", depth="detailed", instructions="", whisper_fallback=False,
                runtime="fake", recipe_json="{}", compiler_strategy="gkt",
            ),
        )

    run_id = database.list_run_statuses()[0][0]
    assert database.get_run_state(run_id) == "external_outcome_unknown"
    assert [request.task for request in harness.requests] == ["knowledge_extract"]


@pytest.mark.asyncio
async def test_gkt_pipeline_runs_one_local_annotation_without_increasing_frontier_calls(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=10_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=10_000, text="The transcript is grounded."),),
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    harness = GroundedTreeHarness()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path),
        transcripts=TranscriptService([StaticTranscriptProvider(transcript)]),
        harness=harness,
    )
    plan = build_execution_plan(
        frontier_runtime_id="fake",
        requested_task_runtimes={"transcript_annotate": "ollama"},
        local_accelerator_requested=True,
        local_accelerator_available=True,
        max_input_tokens=None,
        reserved_output_tokens=0,
    )

    await pipeline.analyze(
        source.canonical_url,
        AnalysisConfig(
            language="en", depth="detailed", instructions="", whisper_fallback=False,
            runtime="fake", recipe_json="{}", compiler_strategy="gkt", execution_plan=plan,
        ),
    )

    assert [request.task for request in harness.requests] == ["transcript_annotate", "knowledge_extract"]


@pytest.mark.asyncio
async def test_pipeline_marks_pack_partial_with_failed_topic_range(tmp_path: Path) -> None:
    source = SourceIdentity(source_id="youtube:abcDEF_1234", video_id="abcDEF_1234", canonical_url="https://www.youtube.com/watch?v=abcDEF_1234")
    transcript = Transcript(source=source, language="en", duration_ms=11 * 60_000, provenance=Provenance.MANUAL_SUBTITLE, segments=tuple(TranscriptSegment(start_ms=index * 60_000, end_ms=(index + 1) * 60_000, text=f"segment {index}") for index in range(11)))
    database = Database(tmp_path / "state.db")
    database.initialize()
    pipeline = AnalysisPipeline(database=database, artifacts=ArtifactStore(tmp_path), transcripts=TranscriptService([StaticTranscriptProvider(transcript)]), harness=PartiallyFailingHarness())

    result = await pipeline.analyze(source.canonical_url, AnalysisConfig(language="en", depth="detailed", instructions="", whisper_fallback=False, runtime="fake", recipe_json="{}"))

    assert result.pack.completion_status == "partial"
    assert result.pack.failed_topic_ids == ("full-video-topic-001",)
    assert result.pack.missing_ranges[0].start_ms == 0


@pytest.mark.asyncio
async def test_pipeline_keeps_only_span_validated_evidence_in_knowledge_pack(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="ko",
        duration_ms=60_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=(
            TranscriptSegment(
                start_ms=0,
                end_ms=60_000,
                text="응답 시간이 45퍼센트 감소했습니다.",
            ),
        ),
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path),
        transcripts=TranscriptService([StaticTranscriptProvider(transcript)]),
        harness=EvidenceCandidateHarness(),
    )

    result = await pipeline.analyze(
        source.canonical_url,
        AnalysisConfig(
            language="ko",
            depth="detailed",
            instructions="",
            whisper_fallback=False,
            runtime="fake",
            recipe_json="{}",
        ),
    )

    claim = result.pack.topics[0].claims[0]
    assert claim.evidence[0].text == "응답 시간이 45퍼센트 감소했습니다."
    assert claim.evidence_refs[0].segment_indexes == (0,)
    measurements = database.list_job_measurements(result.run_id + ":topic:full-video-topic-001")
    assert [measurement[1] for measurement in measurements] == ["topic_summary", "evidence_validation"]
    assert measurements[1][5]["candidate_count"] == 1
    assert measurements[1][5]["valid_count"] == 1


class RecordingTranscriptService:
    def __init__(self, transcript: Transcript) -> None:
        self.transcript = transcript
        self.include_optional: bool | None = None
        self.calls = 0

    async def resolve(
        self, source: SourceIdentity, language: str, *, include_optional: bool = False
    ) -> TranscriptResolution:
        self.calls += 1
        self.include_optional = include_optional
        transcript = self.transcript.model_copy(update={"source": source, "language": language})
        return TranscriptResolution(transcript, "fixture", ())


@pytest.mark.asyncio
async def test_pipeline_reuses_completed_pack_for_same_url(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="ko",
        duration_ms=10 * 60_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=tuple(
            TranscriptSegment(
                start_ms=index * 60_000,
                end_ms=(index + 1) * 60_000,
                text=f"segment {index}",
            )
            for index in range(10)
        ),
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    harness = StructuredFakeHarness(break_first_topic=True)
    provider = StaticTranscriptProvider(transcript)
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path),
        transcripts=TranscriptService([provider]),
        harness=harness,
        concurrency=2,
    )

    first = await pipeline.analyze(source.canonical_url, AnalysisConfig(language="ko", depth="detailed", instructions="", whisper_fallback=False, runtime="auto", recipe_json="{}"), title="테스트 영상")
    call_count = len(harness.calls)
    second = await pipeline.analyze(source.canonical_url, AnalysisConfig(language="ko", depth="detailed", instructions="", whisper_fallback=False, runtime="auto", recipe_json="{}"), title="테스트 영상")

    compose_request = next(request for request in harness.requests if request.task == "compose")
    assert compose_request.output_schema == {
        "type": "object",
        "properties": {
            "overview": {"type": "string"},
            "further_study": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["overview", "further_study"],
        "additionalProperties": False,
    }
    assert first.pack.overview == "전체 요약"
    assert first.run_id == second.run_id
    assert second.reused
    assert len(harness.calls) == call_count
    assert harness.calls.count("repair") == 1
    assert provider.calls == 1
    measurements = database.list_job_measurements(first.run_id + ":topic:full-video-topic-001")
    assert [measurement[1] for measurement in measurements] == ["topic_summary", "repair"]


@pytest.mark.asyncio
async def test_pipeline_does_not_reuse_a_pack_after_the_selected_model_changes(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=60_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=60_000, text="Transcript"),),
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    harness = StructuredFakeHarness()
    harness.model = "fake-model-a"  # type: ignore[attr-defined]
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path),
        transcripts=TranscriptService([StaticTranscriptProvider(transcript)]),
        harness=harness,
    )
    config = AnalysisConfig(
        language="en",
        depth="detailed",
        instructions="",
        whisper_fallback=False,
        runtime="fake",
        recipe_json="{}",
    )

    await pipeline.analyze(source.canonical_url, config)
    harness.model = "fake-model-b"  # type: ignore[attr-defined]
    second = await pipeline.analyze(source.canonical_url, config)

    assert second.reused is False


@pytest.mark.asyncio
async def test_pipeline_enables_optional_transcript_provider_from_settings(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="ko",
        duration_ms=60_000,
        provenance=Provenance.WHISPER,
        segments=(TranscriptSegment(start_ms=0, end_ms=60_000, text="음성 인식 결과"),),
    )
    transcripts = RecordingTranscriptService(transcript)
    database = Database(tmp_path / "state.db")
    database.initialize()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path),
        transcripts=transcripts,  # type: ignore[arg-type]
        harness=StructuredFakeHarness(),
    )

    await pipeline.analyze(source.canonical_url, AnalysisConfig(language="ko", depth="detailed", instructions="", whisper_fallback=True, runtime="auto", recipe_json="{}"))

    assert transcripts.include_optional is True


@pytest.mark.asyncio
async def test_pipeline_preprocesses_topic_input_and_reports_stats(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=60_000,
        provenance=Provenance.AUTO_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=60_000, text="um useful evidence"),),
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    harness = StructuredFakeHarness()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path),
        transcripts=TranscriptService([StaticTranscriptProvider(transcript)]),
        harness=harness,
    )

    result = await pipeline.analyze(
        source.canonical_url,
        AnalysisConfig(
            language="en",
            depth="detailed",
            instructions="",
            whisper_fallback=False,
            runtime="fake",
            recipe_json="{}",
            preprocess_transcript=True,
        ),
    )

    topic_request = next(request for request in harness.requests if request.task == "topic_summary")
    assert topic_request.input["segments"][0]["text"] == "useful evidence"
    assert result.preprocessing_stats is not None
    assert result.preprocessing_stats.removed_filler_count == 1


@pytest.mark.asyncio
async def test_analysis_requests_receive_language_and_common_instructions(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=60_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=60_000, text="Transcript"),),
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    harness = StructuredFakeHarness()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path),
        transcripts=TranscriptService([StaticTranscriptProvider(transcript)]),
        harness=harness,
    )

    await pipeline.analyze(
        source.canonical_url,
        AnalysisConfig(language="en", depth="detailed", instructions="Use plain English.", whisper_fallback=False, runtime="auto", recipe_json="{}"),
    )

    analysis_requests = [request for request in harness.requests if request.task != "repair"]
    assert analysis_requests
    assert all(request.input["language"] == "en" for request in analysis_requests)
    assert all(request.input["user_instructions"] == "Use plain English." for request in analysis_requests)


@pytest.mark.asyncio
async def test_pipeline_analyzes_local_media_and_reuses_same_content_after_move(
    tmp_path: Path,
) -> None:
    first = tmp_path / "meeting.mp3"
    moved = tmp_path / "archive" / "meeting.mp3"
    first.write_bytes(b"local media content")
    moved.parent.mkdir()
    moved.write_bytes(b"local media content")
    source = normalize_source(str(first))
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=60_000,
        provenance=Provenance.WHISPER,
        segments=(TranscriptSegment(start_ms=0, end_ms=60_000, text="Local recording"),),
        title="meeting",
    )
    transcripts = RecordingTranscriptService(transcript)
    database = Database(tmp_path / "state.db")
    database.initialize()
    pipeline = AnalysisPipeline(
        database=database,
        artifacts=ArtifactStore(tmp_path / "data"),
        transcripts=transcripts,  # type: ignore[arg-type]
        harness=StructuredFakeHarness(),
    )

    first_result = await pipeline.analyze(str(first), AnalysisConfig(language="en", depth="detailed", instructions="", whisper_fallback=False, runtime="auto", recipe_json="{}"))
    moved_result = await pipeline.analyze(str(moved), AnalysisConfig(language="en", depth="detailed", instructions="", whisper_fallback=False, runtime="auto", recipe_json="{}"))

    assert first_result.pack.source.kind == SourceKind.LOCAL_MEDIA
    assert first_result.pack.title == "meeting"
    assert moved_result.reused
    assert first_result.run_id == moved_result.run_id
    assert transcripts.calls == 1
    assert database.get_run_source_locator(first_result.run_id) == str(first.resolve())
