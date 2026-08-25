from __future__ import annotations

from pathlib import Path

import pytest

from chew.application import ApplicationService
from chew.config import Settings
from chew.domain import (
    GenerationRequest,
    GenerationResult,
    KnowledgePack,
    Provenance,
    SourceIdentity,
    Transcript,
    TranscriptSegment,
)
from chew.outputs import OutputCompiler, OutputManifest
from chew.pipeline import AnalysisPipeline, AnalysisResult
from chew.pipeline.engine import AnalysisConfig
from chew.storage.artifacts import ArtifactStore
from chew.storage.database import Database
from chew.transcripts.service import TranscriptService


class Harness:
    runtime_id = "fake"

    async def prepare(self) -> None:
        raise AssertionError("local reuse must not probe or prepare a runtime")


class Pipeline:
    def __init__(self, pack: KnowledgePack, usage: dict[str, int] | None = None) -> None:
        self.harness = Harness()
        self.pack = pack
        self.usage = usage
        self.configs: list[AnalysisConfig] = []
        self.sources: list[str] = []

    async def analyze(
        self, url: str, config: AnalysisConfig, *, transcript: Transcript | None = None
    ) -> AnalysisResult:
        self.sources.append(url)
        self.configs.append(config)
        self.transcript = transcript
        return AnalysisResult("run-1", self.pack, len(self.configs) > 1, usage=self.usage)


class Compiler:
    def __init__(self) -> None:
        self.settings: list[Settings] = []

    async def compile(
        self,
        pack: KnowledgePack,
        profile: str,
        settings: Settings,
        destination: Path,
    ) -> OutputManifest:
        self.settings.append(settings)
        destination.mkdir(parents=True, exist_ok=True)
        path = destination / "index.md"
        path.write_text(profile)
        return OutputManifest(profile, profile, (path,))


@pytest.mark.asyncio
async def test_output_profile_does_not_change_analysis_settings(tmp_path: Path) -> None:
    (tmp_path / "YTSUM.md").write_text("공통 분석 지침")
    profiles = tmp_path / ".chew" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "blog.md").write_text("블로그 전용 문체")
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    pack = KnowledgePack(
        source=source,
        title="title",
        language="ko",
        overview="overview",
        transcript_fingerprint="a" * 64,
        topics=(),
        chapters=(),
        analysis_fingerprint="b" * 64,
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    database.create_run("run-1", source.source_id, "key")
    pipeline = Pipeline(pack)
    compiler = Compiler()
    application = ApplicationService(
        pipeline,
        compiler,
        database,
        working_directory=tmp_path,  # type: ignore[arg-type]
    )
    await application.generate(source.canonical_url, "digest", tmp_path / "digest")
    await application.generate(source.canonical_url, "blog", tmp_path / "blog")
    assert pipeline.configs[0].instructions == pipeline.configs[1].instructions
    assert "블로그 전용 문체" not in pipeline.configs[1].instructions
    assert "블로그 전용 문체" in compiler.settings[1].instructions


@pytest.mark.asyncio
async def test_application_compiles_frontier_execution_plan_before_pipeline_run(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    pack = KnowledgePack(
        source=source,
        title="title",
        language="ko",
        overview="overview",
        transcript_fingerprint="a" * 64,
        topics=(),
        chapters=(),
        analysis_fingerprint="b" * 64,
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    database.create_run("run-1", source.source_id, "key")
    pipeline = Pipeline(pack)
    application = ApplicationService(
        pipeline,  # type: ignore[arg-type]
        Compiler(),  # type: ignore[arg-type]
        database,
        working_directory=tmp_path,
    )
    settings = Settings(runtime="gemini", max_input_tokens=3_200, reserved_output_tokens=400)

    await application._generate(source.canonical_url, "digest", tmp_path / "digest", settings, settings)

    plan = pipeline.configs[0].execution_plan
    assert plan is not None
    assert plan.runtime_for("topic_summary") == "gemini"
    assert plan.plan_fingerprint


@pytest.mark.asyncio
async def test_application_passes_user_transcript_to_pipeline(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    pack = KnowledgePack(
        source=source,
        title="title",
        language="en",
        overview="overview",
        transcript_fingerprint="a" * 64,
        topics=(),
        chapters=(),
        analysis_fingerprint="b" * 64,
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    database.create_run("run-1", source.source_id, "key")
    transcript_path = tmp_path / "captions.vtt"
    transcript_path.write_text(
        "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nA user-provided caption", encoding="utf-8"
    )
    pipeline = Pipeline(pack)
    application = ApplicationService(
        pipeline, Compiler(), database, working_directory=tmp_path  # type: ignore[arg-type]
    )

    await application.generate(
        source.canonical_url, "digest", tmp_path / "digest", transcript_path=transcript_path
    )

    assert pipeline.transcript.provenance is Provenance.USER_PROVIDED
    assert pipeline.transcript.source == source


@pytest.mark.asyncio
async def test_resume_uses_the_analysis_recipe_stored_with_the_run(tmp_path: Path) -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    pack = KnowledgePack(
        source=source,
        title="title",
        language="ko",
        overview="overview",
        transcript_fingerprint="a" * 64,
        topics=(),
        chapters=(),
        analysis_fingerprint="b" * 64,
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    stored = Settings(runtime="gemini", depth="deep", instructions="stored recipe")
    database.create_run("run-1", source.source_id, "key", recipe_json=stored.model_dump_json())
    pipeline = Pipeline(pack)
    application = ApplicationService(
        pipeline,  # type: ignore[arg-type]
        Compiler(),  # type: ignore[arg-type]
        database,
        working_directory=tmp_path,
    )

    await application.resume("run-1")

    assert pipeline.configs[0].runtime == "gemini"
    assert pipeline.configs[0].depth == "deep"
    assert pipeline.configs[0].instructions == "stored recipe"


@pytest.mark.asyncio
async def test_resume_uses_stored_local_media_locator(tmp_path: Path) -> None:
    media = tmp_path / "meeting.mp3"
    media.write_bytes(b"audio")
    source = SourceIdentity(
        source_id="local:abc",
        canonical_url=media.resolve().as_uri(),
        kind="local_media",
        local_path=str(media.resolve()),
    )
    pack = KnowledgePack(
        source=source,
        title="meeting",
        language="en",
        overview="overview",
        transcript_fingerprint="a" * 64,
        topics=(),
        chapters=(),
        analysis_fingerprint="b" * 64,
    )
    database = Database(tmp_path / "state.db")
    database.initialize()
    database.create_run(
        "run-1",
        source.source_id,
        "key",
        source_locator=str(media.resolve()),
    )
    pipeline = Pipeline(pack)
    application = ApplicationService(
        pipeline,  # type: ignore[arg-type]
        Compiler(),  # type: ignore[arg-type]
        database,
        working_directory=tmp_path,
    )

    await application.resume("run-1")

    assert pipeline.sources == [str(media.resolve())]


class OfflineProvider:
    name = "fixture"

    def __init__(self, transcript: Transcript) -> None:
        self.transcript = transcript
        self.calls = 0

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript:
        self.calls += 1
        return self.transcript.model_copy(update={"source": source, "language": language})


class OfflineHarness:
    runtime_id = "fake"

    def __init__(self) -> None:
        self.tasks: list[str] = []
        self.fail_on_generate = False

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.fail_on_generate:
            raise AssertionError("cached analysis and output must not call the harness")
        self.tasks.append(request.task)
        if request.task == "knowledge_extract":
            output: dict[str, object] = {
                "thesis_claim_id": "claim-1",
                "claims": [
                    {"claim_id": "claim-1", "text": "자막", "occurrence_ids": ["occurrence-1"]}
                ],
                "occurrences": [
                    {
                        "occurrence_id": "occurrence-1",
                        "raw_segment_indexes": [0],
                        "quote": "자막",
                    }
                ],
            }
        elif request.task == "topic_summary":
            output: dict[str, object] = {
                "topic_id": request.input["topic_id"],
                "title": request.input["title"],
                "summary": "topic",
                "claims": [],
                "concepts": [],
                "examples": [],
            }
        elif request.task == "chapter_summary":
            output = {
                "chapter_id": request.input["chapter_id"],
                "title": request.input["title"],
                "summary": "chapter",
                "topic_ids": request.input["topic_ids"],
            }
        elif request.task == "compose":
            output = {"overview": "overview", "further_study": ["next"]}
        elif request.task == "output_outline":
            output = {"sections": ["one"]}
        elif request.task == "output_compose":
            output = {"markdown": "# Blog\n\nbody"}
        else:
            output = {"markdown": request.input["markdown"], "valid": True}
        return GenerationResult(request_id=request.request_id, output=output, runtime_id=self.runtime_id)


@pytest.mark.asyncio
async def test_profile_changes_reassemble_without_reanalyzing_and_output_cache_is_offline(
    tmp_path: Path,
) -> None:
    (tmp_path / "YTSUM.md").write_text("---\nlanguage: ko\n---\n공통 지침")
    profiles = tmp_path / ".chew" / "profiles"
    profiles.mkdir(parents=True)
    blog_profile = profiles / "blog.md"
    blog_profile.write_text("첫 문체")
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
        segments=(TranscriptSegment(start_ms=0, end_ms=60_000, text="자막"),),
    )
    provider = OfflineProvider(transcript)
    harness = OfflineHarness()
    database = Database(tmp_path / "state.db")
    database.initialize()
    artifacts = ArtifactStore(tmp_path / "data")
    application = ApplicationService(
        AnalysisPipeline(
            database=database,
            artifacts=artifacts,
            transcripts=TranscriptService([provider]),
            harness=harness,
        ),
        OutputCompiler(harness, database=database, artifacts=artifacts),
        database,
        working_directory=tmp_path,
    )

    await application.generate(source.canonical_url, "digest", tmp_path / "digest")
    await application.generate(source.canonical_url, "blog", tmp_path / "blog-one")
    blog_profile.write_text("둘째 문체")
    await application.generate(source.canonical_url, "blog", tmp_path / "blog-two")
    calls_before_cache_restore = list(harness.tasks)
    harness.fail_on_generate = True
    restored = await application.generate(source.canonical_url, "blog", tmp_path / "blog-restored")

    assert provider.calls == 1
    assert calls_before_cache_restore == ["knowledge_extract"]
    assert restored.reused
    target_file = tmp_path / "blog-two" / restored.files[0].name
    assert restored.files[0].read_text() == target_file.read_text()


@pytest.mark.asyncio
async def test_service_forwards_usage_to_command_result(tmp_path: Path) -> None:
    """CommandResult.usage is populated from AnalysisResult.usage."""
    (tmp_path / "YTSUM.md").write_text("---\nlanguage: en\n---\n")
    source = SourceIdentity(
        source_id="youtube:abc1234567",
        video_id="abc1234567",
        canonical_url="https://www.youtube.com/watch?v=abc1234567",
    )
    pack = KnowledgePack(
        source=source,
        title="t",
        language="en",
        overview="o",
        transcript_fingerprint="a" * 64,
        topics=(),
        chapters=(),
        further_study=(),
        analysis_fingerprint="b" * 64,
    )
    pipeline = Pipeline(pack, usage={"input_tokens": 100, "output_tokens": 50})
    compiler = Compiler()
    database = Database(tmp_path / "state.sqlite3")
    database.initialize()
    database.create_run("run-1", source.source_id, "key")
    service = ApplicationService(pipeline, compiler, database, working_directory=tmp_path)
    result = await service.generate(
        "https://www.youtube.com/watch?v=abc1234567",
        "digest",
        tmp_path / "out",
    )
    assert result.usage == {"input_tokens": 100, "output_tokens": 50}


@pytest.mark.asyncio
async def test_service_converts_settings_to_analysis_config(tmp_path: Path) -> None:
    (tmp_path / "YTSUM.md").write_text("---\nlanguage: en\n---\n지침")
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    pack = KnowledgePack(
        source=source,
        title="title",
        language="en",
        overview="overview",
        transcript_fingerprint="a" * 64,
        topics=(),
        chapters=(),
        further_study=(),
        analysis_fingerprint="b" * 64,
    )
    pipeline = Pipeline(pack)
    compiler = Compiler()
    database = Database(tmp_path / "state.sqlite3")
    database.initialize()
    database.create_run("run-1", source.source_id, "key")
    service = ApplicationService(
        pipeline, compiler, database, working_directory=tmp_path  # type: ignore[arg-type]
    )
    await service.generate(
        "https://www.youtube.com/watch?v=abcDEF_1234",
        "digest",
        tmp_path / "out",
    )
    assert len(pipeline.configs) == 1
    config = pipeline.configs[0]
    assert isinstance(config, AnalysisConfig)
    assert config.language == "en"


@pytest.mark.asyncio
async def test_service_converts_harness_auth_error_to_authentication_required(tmp_path: Path) -> None:
    """HarnessAuthenticationError from the pipeline layer is surfaced as AuthenticationRequired.

    This closes the gap between scheduler-level tests (which verify HarnessAuthenticationError
    propagates out of Scheduler.run()) and CLI-level tests (which verify AuthenticationRequired
    gives exit code 2). The service.py conversion at lines 88-89 is the untested link.
    """
    from chew.application import AuthenticationRequired
    from chew.harness.builtin import HarnessAuthenticationError

    class AuthFailPipeline:
        harness = None  # ApplicationService only probes harness when it's a HarnessRegistry

        async def analyze(self, url: str, config: AnalysisConfig) -> object:
            raise HarnessAuthenticationError("codex", "codex login")

    database = Database(tmp_path / "state.db")
    database.initialize()
    database.create_run("run-1", "youtube:abcDEF_1234", "key")

    service = ApplicationService(
        AuthFailPipeline(),  # type: ignore[arg-type]
        Compiler(),
        database,
        working_directory=tmp_path,
    )

    with pytest.raises(AuthenticationRequired) as exc_info:
        await service.generate(
            "https://www.youtube.com/watch?v=abcDEF_1234",
            "digest",
            tmp_path / "out",
        )

    assert exc_info.value.runtime_id == "codex"
    assert "codex login" in str(exc_info.value)
