"""Vendor-neutral immutable domain models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Provenance(StrEnum):
    MANUAL_SUBTITLE = "manual_subtitle"
    AUTO_SUBTITLE = "auto_subtitle"
    TRANSCRIPT_API = "transcript_api"
    USER_PROVIDED = "user_provided"
    WHISPER = "whisper"
    SOURCE = "source"
    AI_EXPLANATION = "ai_explanation"
    EXTERNAL_RESEARCH = "external_research"


class SourceKind(StrEnum):
    YOUTUBE = "youtube"
    LOCAL_MEDIA = "local_media"


class SourceIdentity(FrozenModel):
    source_id: str
    video_id: str | None = None
    canonical_url: str
    kind: SourceKind = SourceKind.YOUTUBE
    local_path: str | None = None

    @model_validator(mode="after")
    def validate_locator(self) -> SourceIdentity:
        if self.kind == SourceKind.YOUTUBE and not self.video_id:
            raise ValueError("YouTube sources require a video ID")
        if self.kind == SourceKind.LOCAL_MEDIA and not self.local_path:
            raise ValueError("local media sources require a path")
        return self


class TranscriptSegment(FrozenModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1)
    speaker: str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> TranscriptSegment:
        if self.end_ms <= self.start_ms:
            raise ValueError("segment end must be after start")
        return self


class Chapter(FrozenModel):
    chapter_id: str
    title: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)


class Transcript(FrozenModel):
    source: SourceIdentity
    language: str = Field(min_length=2)
    duration_ms: int = Field(gt=0)
    provenance: Provenance
    segments: tuple[TranscriptSegment, ...] = Field(min_length=1)
    title: str | None = None
    chapters: tuple[Chapter, ...] = ()

    @model_validator(mode="after")
    def validate_duration(self) -> Transcript:
        if any(segment.end_ms > self.duration_ms for segment in self.segments):
            raise ValueError("segment exceeds transcript duration")
        return self


class Topic(FrozenModel):
    topic_id: str
    chapter_id: str
    title: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    segment_indexes: tuple[int, ...]


class Evidence(FrozenModel):
    text: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    provenance: Provenance = Provenance.SOURCE


class EvidenceCandidate(FrozenModel):
    """An untrusted citation proposed by a generation runtime."""

    segment_indexes: tuple[int, ...] = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    quote: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_range(self) -> EvidenceCandidate:
        if self.end_ms <= self.start_ms:
            raise ValueError("candidate end must be after start")
        if any(index < 0 for index in self.segment_indexes):
            raise ValueError("candidate segment indexes must be non-negative")
        return self


class ValidatedEvidenceRef(FrozenModel):
    """A source citation accepted by deterministic transcript validation."""

    segment_indexes: tuple[int, ...] = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    quote: str = Field(min_length=1)
    raw_transcript_fingerprint: str = Field(min_length=1)


class EvidenceValidationResult(FrozenModel):
    """The validator outcome; invalid candidates cannot carry a trusted reference."""

    valid: bool
    reference: ValidatedEvidenceRef | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> EvidenceValidationResult:
        if self.valid and self.reference is None:
            raise ValueError("valid evidence requires a reference")
        if not self.valid and self.reference is not None:
            raise ValueError("invalid evidence cannot carry a reference")
        return self


class TaskRoute(FrozenModel):
    """An immutable runtime selection for one generation task."""

    task: str = Field(min_length=1)
    runtime_id: str = Field(min_length=1)


class ExecutionPlan(FrozenModel):
    """Policy-owned execution settings that harnesses may consume but not alter."""

    policy_version: str = Field(min_length=1)
    default_runtime_id: str = Field(min_length=1)
    task_routes: tuple[TaskRoute, ...] = ()
    fallback_runtime_id: str = Field(min_length=1)
    local_accelerator_requested: bool = False
    local_accelerator_available: bool | None = None
    max_input_tokens: int | None = Field(default=None, gt=0)
    reserved_output_tokens: int = Field(default=0, ge=0)
    reason: str = Field(min_length=1)
    plan_fingerprint: str = Field(min_length=1)

    def runtime_for(self, task: str) -> str:
        for route in self.task_routes:
            if route.task == task:
                return route.runtime_id
        return self.default_runtime_id


class Claim(FrozenModel):
    text: str
    evidence: tuple[Evidence, ...] = ()
    provenance: Provenance = Provenance.SOURCE

    @model_validator(mode="after")
    def require_source_evidence(self) -> Claim:
        if self.provenance == Provenance.SOURCE and not self.evidence:
            raise ValueError("source claims require evidence")
        return self


class TopicSummary(FrozenModel):
    topic_id: str
    title: str
    summary: str
    claims: tuple[Claim, ...] = ()
    concepts: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()


class ChapterSummary(FrozenModel):
    chapter_id: str
    title: str
    summary: str
    topic_ids: tuple[str, ...]


class MissingRange(FrozenModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)


class KnowledgePack(FrozenModel):
    source: SourceIdentity
    title: str
    language: str
    overview: str
    transcript_fingerprint: str
    topics: tuple[TopicSummary, ...]
    chapters: tuple[ChapterSummary, ...]
    further_study: tuple[str, ...] = ()
    completion_status: str = "complete"
    failed_topic_ids: tuple[str, ...] = ()
    missing_ranges: tuple[MissingRange, ...] = ()
    runtime_id: str | None = None
    model: str | None = None
    analysis_fingerprint: str


class GenerationRequest(FrozenModel):
    request_id: str
    task: str
    input: dict[str, Any]
    output_schema: dict[str, Any]
    timeout_ms: int = Field(default=120_000, gt=0)
    trace_id: str


class GenerationResult(FrozenModel):
    request_id: str
    output: dict[str, Any]
    runtime_id: str
    model: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)
