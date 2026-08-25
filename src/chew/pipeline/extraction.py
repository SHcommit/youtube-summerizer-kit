"""Strict, bounded Frontier extraction of untrusted knowledge tree drafts."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from chew.core.models import GenerationRequest, GenerationResult, KnowledgeTreeDraft
from chew.harness.base import Harness
from chew.pipeline.input_compiler import PreparedTranscript


@dataclass(frozen=True, slots=True)
class AnalysisSpec:
    language: str
    depth: str
    instructions: str


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    draft: KnowledgeTreeDraft
    call_strategy: str
    runtime_id: str
    model: str | None
    usage: dict[str, int]


class ExtractionValidationError(ValueError):
    pass


class KnowledgeExtractor:
    """Run one normal extraction or the fixed two-call over-budget refine path."""

    def __init__(self, harness: Harness) -> None:
        self.harness = harness

    async def extract(
        self, prepared: PreparedTranscript, spec: AnalysisSpec, *, trace_id: str
    ) -> ExtractionResult:
        if prepared.fits_frontier_budget:
            generated = await self._generate("knowledge_extract", prepared, spec, trace_id)
            return self._result(generated, "single_pass")
        outline = await self._generate("knowledge_extract_outline", prepared, spec, trace_id)
        # The refine call carries only the structured outline plus the same stable
        # paragraph IDs; this is the sole permitted second semantic request.
        generated = await self._generate(
            "knowledge_extract_refine", prepared, spec, trace_id, outline=outline.output
        )
        return self._result(generated, "two_pass_refine")

    async def _generate(
        self,
        task: str,
        prepared: PreparedTranscript,
        spec: AnalysisSpec,
        trace_id: str,
        *,
        outline: dict[str, object] | None = None,
    ) -> GenerationResult:
        input_value: dict[str, object] = {
            "prepared_transcript": prepared.render_for_frontier(),
            "prepared_transcript_fingerprint": prepared.fingerprint,
            "language": spec.language,
            "depth": spec.depth,
            "instructions": spec.instructions,
        }
        if outline is not None:
            input_value["outline"] = outline
        return await self.harness.generate(
            GenerationRequest(
                request_id=f"{trace_id}:{task}",
                task=task,
                input=input_value,
                output_schema=KnowledgeTreeDraft.model_json_schema(),
                trace_id=trace_id,
            )
        )

    @staticmethod
    def _result(result: GenerationResult, strategy: str) -> ExtractionResult:
        try:
            draft = KnowledgeTreeDraft.model_validate(result.output)
        except ValidationError as error:
            raise ExtractionValidationError("knowledge extraction did not satisfy the tree schema") from error
        return ExtractionResult(
            draft=draft,
            call_strategy=strategy,
            runtime_id=result.runtime_id,
            model=result.model,
            usage=result.usage,
        )
