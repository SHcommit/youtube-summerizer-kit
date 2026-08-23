from chew.core.models import (
    Provenance,
    SourceIdentity,
    Transcript,
    TranscriptSegment,
)
from chew.pipeline.preprocessing import FillerRemovalStrategy, TranscriptPreprocessor

SOURCE = SourceIdentity(
    source_id="youtube:abcDEF_1234",
    video_id="abcDEF_1234",
    canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
)


def _transcript(*texts: str) -> Transcript:
    return Transcript(
        source=SOURCE,
        language="en",
        duration_ms=len(texts) * 1_000,
        provenance=Provenance.AUTO_SUBTITLE,
        segments=tuple(
            TranscriptSegment(start_ms=index * 1_000, end_ms=(index + 1) * 1_000, text=text)
            for index, text in enumerate(texts)
        ),
    )


def test_filler_removal_keeps_context_sensitive_words() -> None:
    result = FillerRemovalStrategy().process(_transcript("um like you know this is basically great"))

    assert result.segments[0].text == "like this is basically great"


def test_filler_removal_handles_korean_stutter_and_empty_segments() -> None:
    result = FillerRemovalStrategy().process(_transcript("음~ 이이이이게", "어~"))

    assert [segment.text for segment in result.segments] == ["이게"]


def test_preprocessor_reports_applied_strategy_and_savings() -> None:
    original = _transcript("um hello world")
    processed, stats = TranscriptPreprocessor([FillerRemovalStrategy()]).process(original)

    assert processed is not original
    assert stats.applied_strategies == ("filler-removal",)
    assert stats.removed_filler_count == 1
    assert stats.token_reduction_pct > 0
