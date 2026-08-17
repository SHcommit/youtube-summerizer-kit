from pathlib import Path

import pytest

from chew.config import Settings
from chew.domain import (
    ChapterSummary,
    Claim,
    Evidence,
    GenerationRequest,
    GenerationResult,
    KnowledgePack,
    Provenance,
    SourceIdentity,
    TopicSummary,
)
from chew.harness.base import HarnessCapabilities, HarnessProbe
from chew.knowledge import build_knowledge_pack
from chew.pipeline.outputs import OutputCompiler, _safe_name


def pack() -> KnowledgePack:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    topic = TopicSummary(
        topic_id="intro-topic-001",
        title="핵심 개념",
        summary="소주제 설명",
        claims=(
            Claim(
                text="영상의 주장",
                evidence=(Evidence(text="영상 근거", start_ms=65_000, end_ms=70_000),),
                provenance=Provenance.SOURCE,
            ),
        ),
        concepts=("핵심 개념",),
    )
    chapter = ChapterSummary(
        chapter_id="intro",
        title="소개",
        summary="챕터 설명",
        topic_ids=(topic.topic_id,),
    )
    return build_knowledge_pack(
        source=source,
        title="테스트 영상",
        language="ko",
        overview="전체 설명",
        transcript_fingerprint="a" * 64,
        topics=(topic,),
        chapters=(chapter,),
    )


@pytest.mark.asyncio
async def test_digest_renderer_preserves_source_labels_and_timestamps(tmp_path: Path) -> None:
    manifest = await OutputCompiler().compile(pack(), "digest", Settings(), tmp_path / "digest")

    text = manifest.files[0].read_text(encoding="utf-8")
    assert "테스트 영상" in text
    assert "[Source] 영상의 주장" in text
    assert "01:05" in text


@pytest.mark.asyncio
async def test_obsidian_only_links_generated_topic_notes(tmp_path: Path) -> None:
    manifest = await OutputCompiler().compile(pack(), "obsidian", Settings(), tmp_path / "vault")

    index = (tmp_path / "vault" / "index.md").read_text(encoding="utf-8")
    assert "[[핵심 개념]]" in index
    assert (tmp_path / "vault" / "핵심 개념.md") in manifest.files


class OutputHarness:
    runtime_id = "fake"

    def __init__(self) -> None:
        self.tasks: list[str] = []
        self.preferences: list[str] = []

    def set_preference(self, runtime_id: str) -> None:
        self.preferences.append(runtime_id)

    async def probe(self) -> HarnessProbe:
        return HarnessProbe(
            runtime_id="fake",
            available=True,
            auth_ready=True,
            version="1",
            capabilities=HarnessCapabilities(),
            detail=None,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.tasks.append(request.task)
        output: dict[str, object]
        if request.task == "output_outline":
            output = {"sections": ["문제", "핵심", "적용"]}
        elif request.task == "output_compose":
            output = {"markdown": "# 사용자 톤 블로그\n\n정리된 글"}
        else:
            output = {"markdown": request.input["markdown"], "valid": True}
        return GenerationResult(request_id=request.request_id, output=output, runtime_id="fake")


@pytest.mark.asyncio
async def test_blog_uses_plan_compose_verify_and_profile_changes_cache_key(tmp_path: Path) -> None:
    harness = OutputHarness()
    compiler = OutputCompiler(harness)

    first = await compiler.compile(
        pack(),
        "blog",
        Settings(instructions="친근한 기술 블로그 톤"),
        tmp_path / "blog",
    )
    second = await compiler.compile(
        pack(),
        "blog",
        Settings(instructions="간결한 공식 문서 톤"),
        tmp_path / "blog-2",
    )

    assert harness.tasks[:3] == ["output_outline", "output_compose", "output_verify"]
    assert "사용자 톤 블로그" in first.files[0].read_text(encoding="utf-8")
    assert first.cache_key != second.cache_key


@pytest.mark.asyncio
async def test_uncached_ai_output_honors_profile_runtime(tmp_path: Path) -> None:
    harness = OutputHarness()
    await OutputCompiler(harness).compile(
        pack(), "blog", Settings(runtime="gemini"), tmp_path / "blog"
    )

    assert harness.preferences == ["gemini"]


@pytest.mark.asyncio
async def test_same_output_cache_key_restores_without_model_calls(tmp_path: Path) -> None:
    from chew.storage.artifacts import ArtifactStore
    from chew.storage.database import Database

    harness = OutputHarness()
    database = Database(tmp_path / "state.db")
    database.initialize()
    compiler = OutputCompiler(
        harness, database=database, artifacts=ArtifactStore(tmp_path / "data")
    )
    settings = Settings(instructions="고정 문체")
    await compiler.compile(pack(), "blog", settings, tmp_path / "first")
    await compiler.compile(pack(), "blog", settings, tmp_path / "second")
    assert harness.tasks == ["output_outline", "output_compose", "output_verify"]
    filename = f"{_safe_name(pack().title)}.md"
    assert (tmp_path / "second" / filename).read_text() == (
        tmp_path / "first" / filename
    ).read_text()
