from chew.domain import Provenance, SourceIdentity, Transcript, TranscriptSegment
from chew.pipeline.input_compiler import InputBudget, InputCompiler


def _transcript() -> Transcript:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    return Transcript(
        source=source,
        language="en",
        duration_ms=20_000,
        provenance=Provenance.AUTO_SUBTITLE,
        segments=(
            TranscriptSegment(start_ms=0, end_ms=10_000, text="Um, the result is not 10 ms."),
            TranscriptSegment(start_ms=10_000, end_ms=20_000, text="[music] The result is not 10 ms."),
        ),
    )


def test_compiler_keeps_reversible_raw_mapping_and_protected_negation() -> None:
    prepared = InputCompiler().compile(
        _transcript(), InputBudget(max_input_tokens=100, reserved_output_tokens=10)
    )

    assert prepared.paragraphs[0].raw_segment_indexes == (0, 1)
    assert "not 10 ms" in prepared.paragraphs[0].text
    assert prepared.non_speech_markers == ("[music]",)
    assert prepared.raw_transcript_fingerprint
    assert prepared.fits_frontier_budget is True


def test_compiler_reports_budget_overflow_without_deleting_segments() -> None:
    prepared = InputCompiler().compile(_transcript(), InputBudget(max_input_tokens=3, reserved_output_tokens=1))

    assert prepared.fits_frontier_budget is False
    assert prepared.paragraphs[0].raw_segment_indexes == (0, 1)
