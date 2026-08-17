"""Canonical transcript cleanup and quality checks."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from itertools import pairwise

from chew.domain import Transcript, TranscriptSegment


@dataclass(frozen=True, slots=True)
class ValidationReport:
    accepted: bool
    coverage: float
    reasons: tuple[str, ...]


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_transcript(transcript: Transcript) -> Transcript:
    ordered = sorted(transcript.segments, key=lambda segment: (segment.start_ms, segment.end_ms))
    normalized: list[TranscriptSegment] = []
    for segment in ordered:
        text = _clean_text(segment.text)
        if normalized and normalized[-1].text == text and segment.start_ms <= normalized[-1].end_ms:
            previous = normalized[-1]
            normalized[-1] = TranscriptSegment(
                start_ms=previous.start_ms,
                end_ms=max(previous.end_ms, segment.end_ms),
                text=text,
                speaker=previous.speaker,
            )
            continue
        normalized.append(
            TranscriptSegment(
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                text=text,
                speaker=segment.speaker,
            )
        )
    return transcript.model_copy(update={"segments": tuple(normalized)})


def validate_transcript(transcript: Transcript, minimum_coverage: float = 0.6) -> ValidationReport:
    occupied = 0
    cursor = 0
    for segment in sorted(transcript.segments, key=lambda item: item.start_ms):
        start = max(cursor, segment.start_ms)
        if segment.end_ms > start:
            occupied += segment.end_ms - start
        cursor = max(cursor, segment.end_ms)
    coverage = occupied / transcript.duration_ms
    reasons: list[str] = []
    if any(
        current.start_ms < previous.start_ms for previous, current in pairwise(transcript.segments)
    ):
        reasons.append("timestamps_not_monotonic")
    if coverage < minimum_coverage:
        reasons.append("coverage")
    if not any(segment.text.strip() for segment in transcript.segments):
        reasons.append("empty_text")
    meaningful = [
        segment.text.strip().casefold() for segment in transcript.segments if segment.text.strip()
    ]
    repeated = max(Counter(meaningful).values(), default=0)
    if len(meaningful) >= 4 and repeated / len(meaningful) > 0.5:
        reasons.append("excessive_repetition")
    ordered = sorted(transcript.segments, key=lambda item: item.start_ms)
    gaps = [
        *(current.start_ms - previous.end_ms for previous, current in pairwise(ordered)),
        ordered[0].start_ms,
        transcript.duration_ms - ordered[-1].end_ms,
    ]
    maximum_gap = max(gaps)
    if maximum_gap > max(120_000, round(transcript.duration_ms * 0.2)):
        reasons.append("large_gap")
    return ValidationReport(not reasons, coverage, tuple(reasons))
