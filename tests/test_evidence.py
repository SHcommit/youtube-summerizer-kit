import pytest

from chew.core.identity import fingerprint
from chew.domain import (
    EvidenceCandidate,
    Provenance,
    SourceIdentity,
    Transcript,
    TranscriptSegment,
)
from chew.pipeline.evidence import validate_evidence_candidate


@pytest.fixture
def transcript() -> Transcript:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    return Transcript(
        source=source,
        language="ko",
        duration_ms=20_000,
        provenance=Provenance.MANUAL_SUBTITLE,
        segments=(
            TranscriptSegment(start_ms=0, end_ms=5_000, text="오늘은 성능 개선을 설명합니다."),
            TranscriptSegment(start_ms=5_000, end_ms=10_000, text="응답 시간이 45퍼센트 감소했습니다."),
            TranscriptSegment(start_ms=10_000, end_ms=15_000, text="다음으로 재시도 정책을 다룹니다."),
        ),
    )


def test_validator_creates_reference_only_for_quote_anchored_in_raw_segment(transcript: Transcript) -> None:
    candidate = EvidenceCandidate(
        segment_indexes=(1,),
        start_ms=5_500,
        end_ms=9_000,
        quote="응답 시간이 45퍼센트 감소했습니다.",
    )

    result = validate_evidence_candidate(
        candidate,
        transcript=transcript,
        raw_transcript_fingerprint=fingerprint(transcript),
        allowed_segment_indexes=(0, 1, 2),
    )

    assert result.valid is True
    assert result.reference is not None
    assert result.reference.segment_indexes == (1,)
    assert result.reference.raw_transcript_fingerprint == fingerprint(transcript)


def test_validator_rejects_quote_that_model_invented_even_when_timestamp_is_valid(transcript: Transcript) -> None:
    candidate = EvidenceCandidate(
        segment_indexes=(1,),
        start_ms=5_500,
        end_ms=9_000,
        quote="응답 시간이 90퍼센트 감소했습니다.",
    )

    result = validate_evidence_candidate(
        candidate,
        transcript=transcript,
        raw_transcript_fingerprint=fingerprint(transcript),
        allowed_segment_indexes=(0, 1, 2),
    )

    assert result.valid is False
    assert result.reference is None
    assert result.reason == "quote_not_found"


def test_validator_rejects_segment_outside_current_topic(transcript: Transcript) -> None:
    candidate = EvidenceCandidate(
        segment_indexes=(2,),
        start_ms=10_000,
        end_ms=14_000,
        quote="다음으로 재시도 정책을 다룹니다.",
    )

    result = validate_evidence_candidate(
        candidate,
        transcript=transcript,
        raw_transcript_fingerprint=fingerprint(transcript),
        allowed_segment_indexes=(0, 1),
    )

    assert result.valid is False
    assert result.reference is None
    assert result.reason == "segment_not_allowed"
