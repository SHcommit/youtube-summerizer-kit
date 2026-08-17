from chew.domain import Provenance, SourceIdentity, Transcript, TranscriptSegment
from chew.transcripts.validation import normalize_transcript, validate_transcript

SOURCE = SourceIdentity(
    source_id="youtube:abcDEF_1234",
    video_id="abcDEF_1234",
    canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
)


def transcript(*segments: TranscriptSegment, duration_ms: int = 10_000) -> Transcript:
    return Transcript(
        source=SOURCE,
        language="ko",
        duration_ms=duration_ms,
        provenance=Provenance.AUTO_SUBTITLE,
        segments=segments,
    )


def test_normalization_sorts_and_collapses_repeated_captions() -> None:
    value = transcript(
        TranscriptSegment(start_ms=2_000, end_ms=4_000, text=" 반복  문장 "),
        TranscriptSegment(start_ms=0, end_ms=2_000, text="반복 문장"),
        TranscriptSegment(start_ms=4_000, end_ms=8_000, text="새로운 내용"),
    )

    normalized = normalize_transcript(value)

    assert [(item.start_ms, item.end_ms, item.text) for item in normalized.segments] == [
        (0, 4_000, "반복 문장"),
        (4_000, 8_000, "새로운 내용"),
    ]


def test_validation_rejects_low_duration_coverage() -> None:
    value = transcript(TranscriptSegment(start_ms=0, end_ms=1_000, text="너무 짧음"))

    report = validate_transcript(value)

    assert not report.accepted
    assert "coverage" in report.reasons


def test_validation_rejects_large_leading_or_trailing_gap() -> None:
    leading = transcript(
        TranscriptSegment(start_ms=180_000, end_ms=600_000, text="뒤쪽 자막"),
        duration_ms=600_000,
    )
    trailing = transcript(
        TranscriptSegment(start_ms=0, end_ms=420_000, text="앞쪽 자막"),
        duration_ms=600_000,
    )

    assert "large_gap" in validate_transcript(leading).reasons
    assert "large_gap" in validate_transcript(trailing).reasons
