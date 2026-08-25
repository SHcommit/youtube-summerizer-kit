"""Bounded local cleanup annotations with fail-closed validation."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, ValidationError

from chew.core.models import FrozenModel, GenerationRequest
from chew.harness.base import Harness
from chew.pipeline.input_compiler import PreparedTranscript


class AnnotationAction(StrEnum):
    DROP_FILLER = "DROP_FILLER"
    DROP_DUPLICATE = "DROP_DUPLICATE"
    MARK_BOUNDARY = "MARK_BOUNDARY"
    MARK_LOW_CONFIDENCE = "MARK_LOW_CONFIDENCE"


class TranscriptAnnotation(FrozenModel):
    action: AnnotationAction
    raw_segment_indexes: tuple[int, ...] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    reason_code: str = Field(min_length=1)


class AnnotationEnvelope(FrozenModel):
    annotations: tuple[TranscriptAnnotation, ...] = ()


class AnnotationResult(FrozenModel):
    prepared: PreparedTranscript
    accepted: bool
    reason: str | None = None
    sidecar_fingerprint: str | None = None


class TranscriptAnnotator:
    """Ask an already-configured local runtime once; never repair or retry it."""

    def __init__(self, harness: Harness) -> None:
        self.harness = harness

    async def annotate(self, prepared: PreparedTranscript, *, trace_id: str) -> AnnotationResult:
        request = GenerationRequest(
            request_id=f"{trace_id}:local-annotation",
            task="transcript_annotate",
            input={
                "paragraphs": [paragraph.model_dump(mode="json") for paragraph in prepared.paragraphs],
                "allowed_actions": [action.value for action in AnnotationAction],
                "instruction": "Return annotations only; do not generate replacement text, claims, or summaries.",
            },
            output_schema=AnnotationEnvelope.model_json_schema(),
            trace_id=trace_id,
        )
        try:
            result = await self.harness.generate(request)
            sidecar = AnnotationEnvelope.model_validate(result.output)
        except (ValidationError, RuntimeError, TimeoutError, ValueError):
            return AnnotationResult(prepared=prepared, accepted=False, reason="invalid_or_unavailable")
        allowed_indexes = {index for paragraph in prepared.paragraphs for index in paragraph.raw_segment_indexes}
        if any(index not in allowed_indexes for item in sidecar.annotations for index in item.raw_segment_indexes):
            return AnnotationResult(prepared=prepared, accepted=False, reason="unknown_segment")
        # Annotation is deliberately a sidecar at this boundary. Applying a deletion
        # requires a later protected-span policy check, so an accepted sidecar never
        # mutates the raw-to-prepared mapping in place.
        from chew.core.identity import fingerprint

        return AnnotationResult(
            prepared=prepared,
            accepted=True,
            sidecar_fingerprint=fingerprint(sidecar),
        )
