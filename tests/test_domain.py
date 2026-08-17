import pytest
from pydantic import ValidationError

from chew.domain import Claim, Provenance, SourceIdentity, Transcript, TranscriptSegment


def test_domain_models_are_immutable() -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )

    with pytest.raises(ValidationError):
        source.video_id = "other"  # type: ignore[misc]


def test_transcript_rejects_segments_beyond_duration() -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )

    with pytest.raises(ValidationError, match="duration"):
        Transcript(
            source=source,
            language="ko",
            duration_ms=1_000,
            provenance=Provenance.MANUAL_SUBTITLE,
            segments=(TranscriptSegment(start_ms=500, end_ms=1_500, text="내용"),),
        )


def test_source_claim_requires_timestamped_evidence() -> None:
    with pytest.raises(ValidationError, match="source claims require evidence"):
        Claim(text="영상에서 확인한 주장", provenance=Provenance.SOURCE)


def test_ai_explanation_can_be_explicitly_ungrounded() -> None:
    claim = Claim(text="AI가 추가한 설명", provenance=Provenance.AI_EXPLANATION)

    assert claim.evidence == ()
