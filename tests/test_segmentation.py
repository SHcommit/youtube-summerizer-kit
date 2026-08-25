from chew.domain import Chapter, Provenance, SourceIdentity, Transcript, TranscriptSegment
from chew.segmentation import SegmentationPolicy, segment_transcript

SOURCE = SourceIdentity(
    source_id="youtube:abcDEF_1234",
    video_id="abcDEF_1234",
    canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
)


def make_transcript(minutes: int) -> Transcript:
    segments = tuple(
        TranscriptSegment(
            start_ms=index * 60_000,
            end_ms=(index + 1) * 60_000,
            text=f"segment {index}",
        )
        for index in range(minutes)
    )
    return Transcript(
        source=SOURCE,
        language="ko",
        duration_ms=minutes * 60_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=segments,
    )


def test_short_youtube_chapters_are_preserved() -> None:
    transcript = make_transcript(12)
    chapters = (
        Chapter(chapter_id="intro", title="소개", start_ms=0, end_ms=6 * 60_000),
        Chapter(chapter_id="core", title="핵심", start_ms=6 * 60_000, end_ms=12 * 60_000),
    )

    manifest = segment_transcript(transcript, chapters, SegmentationPolicy())

    assert [(topic.chapter_id, topic.start_ms, topic.end_ms) for topic in manifest.topics] == [
        ("intro", 0, 6 * 60_000),
        ("core", 6 * 60_000, 12 * 60_000),
    ]


def test_long_chapter_is_subdivided_within_maximum_window() -> None:
    transcript = make_transcript(24)
    chapters = (Chapter(chapter_id="all", title="전체", start_ms=0, end_ms=24 * 60_000),)

    manifest = segment_transcript(
        transcript,
        chapters,
        SegmentationPolicy(target_ms=5 * 60_000, maximum_ms=10 * 60_000),
    )

    assert len(manifest.topics) > 1
    assert all(topic.end_ms - topic.start_ms <= 10 * 60_000 for topic in manifest.topics)


def test_missing_chapters_uses_adaptive_windows_and_covers_every_segment() -> None:
    transcript = make_transcript(23)

    manifest = segment_transcript(transcript, (), SegmentationPolicy())

    covered = {index for topic in manifest.topics for index in topic.segment_indexes}
    assert covered == set(range(len(transcript.segments)))
    assert manifest.chapters[0].title == "전체 영상"


def test_overlap_is_bounded_to_neighboring_context() -> None:
    transcript = make_transcript(12)

    manifest = segment_transcript(
        transcript,
        (),
        SegmentationPolicy(target_ms=5 * 60_000, overlap_ms=60_000),
    )

    first, second = manifest.topics[:2]
    assert len(set(first.segment_indexes) & set(second.segment_indexes)) <= 1


def test_punctuation_boundary_can_adjust_fixed_target() -> None:
    segments = (
        TranscriptSegment(start_ms=0, end_ms=270_000, text="첫 소주제가 끝납니다."),
        TranscriptSegment(start_ms=280_000, end_ms=600_000, text="다음 소주제"),
        TranscriptSegment(start_ms=600_000, end_ms=720_000, text="마무리"),
    )
    transcript = Transcript(
        source=SOURCE,
        language="ko",
        duration_ms=720_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=segments,
    )
    manifest = segment_transcript(transcript, (), SegmentationPolicy())
    assert manifest.topics[0].end_ms == 270_000


def test_explicit_token_budget_splits_before_time_limit() -> None:
    transcript = Transcript(
        source=SOURCE,
        language="en",
        duration_ms=180_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=tuple(
            TranscriptSegment(
                start_ms=index * 60_000,
                end_ms=(index + 1) * 60_000,
                text="word " * 10,
            )
            for index in range(3)
        ),
    )

    manifest = segment_transcript(
        transcript,
        (),
        SegmentationPolicy(max_input_tokens=12, reserved_output_tokens=2),
    )

    assert [topic.segment_indexes for topic in manifest.topics] == [(0,), (1,), (2,)]


def test_coalescing_does_not_treat_korean_text_as_a_depth_mode() -> None:
    chapters = tuple(
        Chapter(chapter_id=f"chapter-{index}", title=str(index), start_ms=index, end_ms=index + 1)
        for index in range(4)
    )

    assert len(segment_transcript(make_transcript(12), chapters, SegmentationPolicy(), depth="핵심").chapters) == 4
