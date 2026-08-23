"""Deterministic validation for model-proposed transcript citations."""

from __future__ import annotations

import re

from chew.core.models import (
    EvidenceCandidate,
    EvidenceValidationResult,
    Transcript,
    TranscriptSegment,
    ValidatedEvidenceRef,
)

_WHITESPACE = re.compile(r"\s+")


def _normalized(value: str) -> str:
    return _WHITESPACE.sub("", value).casefold()


def _invalid(reason: str) -> EvidenceValidationResult:
    return EvidenceValidationResult(valid=False, reason=reason)


def validate_evidence_candidate(
    candidate: EvidenceCandidate,
    *,
    transcript: Transcript,
    raw_transcript_fingerprint: str,
    allowed_segment_indexes: tuple[int, ...],
) -> EvidenceValidationResult:
    """Return a trusted reference only when the candidate is anchored in raw text."""

    allowed = set(allowed_segment_indexes)
    if any(index not in allowed for index in candidate.segment_indexes):
        return _invalid("segment_not_allowed")
    if any(index >= len(transcript.segments) for index in candidate.segment_indexes):
        return _invalid("segment_not_found")

    referenced = tuple(transcript.segments[index] for index in candidate.segment_indexes)
    if not _overlaps_referenced_range(candidate, referenced):
        return _invalid("timestamp_out_of_range")

    searchable = _searchable_segments(candidate.segment_indexes, transcript.segments, allowed)
    if _normalized(candidate.quote) not in _normalized(" ".join(segment.text for segment in searchable)):
        return _invalid("quote_not_found")

    return EvidenceValidationResult(
        valid=True,
        reference=ValidatedEvidenceRef(
            segment_indexes=candidate.segment_indexes,
            start_ms=candidate.start_ms,
            end_ms=candidate.end_ms,
            quote=candidate.quote,
            raw_transcript_fingerprint=raw_transcript_fingerprint,
        ),
    )


def _overlaps_referenced_range(candidate: EvidenceCandidate, segments: tuple[TranscriptSegment, ...]) -> bool:
    return any(candidate.start_ms < segment.end_ms and candidate.end_ms > segment.start_ms for segment in segments)


def _searchable_segments(
    indexes: tuple[int, ...],
    segments: tuple[TranscriptSegment, ...],
    allowed: set[int],
) -> tuple[TranscriptSegment, ...]:
    search_indexes = set(indexes)
    for index in indexes:
        for adjacent in (index - 1, index + 1):
            if adjacent in allowed:
                search_indexes.add(adjacent)
    return tuple(segments[index] for index in sorted(search_indexes))
