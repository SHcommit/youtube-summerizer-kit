import pytest

from chew.domain import (
    GenerationRequest,
    GenerationResult,
    Provenance,
    SourceIdentity,
    Transcript,
    TranscriptSegment,
)
from chew.pipeline.extraction import AnalysisSpec, ExtractionValidationError, KnowledgeExtractor
from chew.pipeline.input_compiler import InputBudget, InputCompiler


class ExtractionHarness:
    runtime_id = "fake"

    def __init__(self, output: dict[str, object]) -> None:
        self.output = output
        self.requests: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)
        return GenerationResult(request_id=request.request_id, output=self.output, runtime_id=self.runtime_id)


def _transcript() -> Transcript:
    source = SourceIdentity(
        source_id="youtube:abcDEF_1234",
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    return Transcript(
        source=source,
        language="en",
        duration_ms=10_000,
        provenance=Provenance.AUTO_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=10_000, text="bounded cleanup."),),
    )


def _draft() -> dict[str, object]:
    return {
        "thesis_claim_id": "claim-1",
        "claims": [{"claim_id": "claim-1", "text": "Bounded cleanup.", "occurrence_ids": ["occ-1"]}],
        "occurrences": [{"occurrence_id": "occ-1", "raw_segment_indexes": [0], "quote": "bounded cleanup."}],
    }


@pytest.mark.asyncio
async def test_in_budget_extraction_issues_one_structured_frontier_request() -> None:
    prepared = InputCompiler().compile(_transcript(), InputBudget(max_input_tokens=100))
    harness = ExtractionHarness(_draft())

    result = await KnowledgeExtractor(harness).extract(
        prepared, AnalysisSpec(language="en", depth="normal", instructions=""), trace_id="run-1"
    )

    assert result.call_strategy == "single_pass"
    assert result.draft.thesis_claim_id == "claim-1"
    assert [request.task for request in harness.requests] == ["knowledge_extract"]


@pytest.mark.asyncio
async def test_invalid_extraction_output_does_not_trigger_repair() -> None:
    prepared = InputCompiler().compile(_transcript(), InputBudget(max_input_tokens=100))
    harness = ExtractionHarness({"invalid": True})

    with pytest.raises(ExtractionValidationError):
        await KnowledgeExtractor(harness).extract(
            prepared, AnalysisSpec(language="en", depth="normal", instructions=""), trace_id="run-1"
        )

    assert [request.task for request in harness.requests] == ["knowledge_extract"]
