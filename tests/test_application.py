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
from chew.storage.artifacts import ArtifactStore
from chew.storage.database import Database
from chew.transcripts.service import TranscriptService


class Harness:
    runtime_id = "fake"

    async def prepare(self) -> None:
        raise AssertionError("local reuse must not probe or prepare a runtime")


class Pipeline:
    def __init__(self, pack: KnowledgePack) -> None:
        self.harness = Harness()
        self.pack = pack
        self.settings: list[Settings] = []
        self.sources: list[str] = []

    async def analyze(self, url: str, settings: Settings) -> AnalysisResult:
        self.sources.append(url)
        self.settings.append(settings)
        return AnalysisResult("run-1", self.pack, len(self.settings) > 1)


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
    assert pipeline.settings[0].instructions == pipeline.settings[1].instructions
    assert "블로그 전용 문체" not in pipeline.settings[1].instructions
    assert "블로그 전용 문체" in compiler.settings[1].instructions


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

    assert pipeline.settings[0].runtime == "gemini"
    assert pipeline.settings[0].depth == "deep"
    assert pipeline.settings[0].instructions == "stored recipe"


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
        if request.task == "topic_summary":
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
    assert calls_before_cache_restore.count("topic_summary") == 1
    assert calls_before_cache_restore.count("chapter_summary") == 1
    assert calls_before_cache_restore.count("compose") == 1
    assert calls_before_cache_restore.count("output_compose") == 2
    assert restored.reused
    target_file = tmp_path / "blog-two" / restored.files[0].name
    assert restored.files[0].read_text() == target_file.read_text()
