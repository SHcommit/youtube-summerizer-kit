import pytest

from chew.domain import GenerationRequest, GenerationResult, Provenance, SourceIdentity, Transcript, TranscriptSegment
from chew.pipeline.annotation import TranscriptAnnotator
from chew.pipeline.input_compiler import InputBudget, InputCompiler


class InvalidAnnotationHarness:
    runtime_id = "ollama"

    def __init__(self) -> None:
        self.requests: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)
        return GenerationResult(
            request_id=request.request_id,
            runtime_id=self.runtime_id,
            output={
                "annotations": [
                    {
                        "action": "DROP_FILLER",
                        "raw_segment_indexes": [999],
                        "confidence": 0.9,
                        "reason_code": "filler",
                    }
                ]
            },
        )


@pytest.mark.asyncio
async def test_invalid_annotation_is_rejected_without_a_retry() -> None:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=10_000,
        provenance=Provenance.AUTO_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=10_000, text="Um, bounded cleanup."),),
    )
    prepared = InputCompiler().compile(transcript, InputBudget(max_input_tokens=100))
    harness = InvalidAnnotationHarness()

    result = await TranscriptAnnotator(harness).annotate(prepared, trace_id="run-1")

    assert result.accepted is False
    assert result.prepared == prepared
    assert result.reason == "unknown_segment"
    assert [request.task for request in harness.requests] == ["transcript_annotate"]
