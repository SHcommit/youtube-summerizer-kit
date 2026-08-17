from chew.domain import (
    ChapterSummary,
    Claim,
    Evidence,
    Provenance,
    SourceIdentity,
    TopicSummary,
)
from chew.knowledge import build_knowledge_pack


def test_knowledge_pack_preserves_evidence_and_has_stable_fingerprint() -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    topic = TopicSummary(
        topic_id="chapter-1-topic-001",
        title="핵심",
        summary="요약",
        claims=(
            Claim(
                text="주장",
                evidence=(Evidence(text="근거", start_ms=1_000, end_ms=2_000),),
                provenance=Provenance.SOURCE,
            ),
        ),
    )
    chapter = ChapterSummary(
        chapter_id="chapter-1",
        title="첫 장",
        summary="장 요약",
        topic_ids=(topic.topic_id,),
    )

    first = build_knowledge_pack(
        source=source,
        title="영상",
        language="ko",
        overview="전체 요약",
        transcript_fingerprint="a" * 64,
        topics=(topic,),
        chapters=(chapter,),
        further_study=("추가 개념",),
    )
    second = build_knowledge_pack(
        source=source,
        title="영상",
        language="ko",
        overview="전체 요약",
        transcript_fingerprint="a" * 64,
        topics=(topic,),
        chapters=(chapter,),
        further_study=("추가 개념",),
    )

    assert first.analysis_fingerprint == second.analysis_fingerprint
    assert first.topics[0].claims[0].evidence[0].start_ms == 1_000
