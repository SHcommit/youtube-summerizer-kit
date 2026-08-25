"""Chapter-first deterministic transcript segmentation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from chew.core.models import Chapter, Topic, Transcript


@dataclass(frozen=True, slots=True)
class SegmentationPolicy:
    target_ms: int = 5 * 60_000
    maximum_ms: int = 10 * 60_000
    overlap_ms: int = 15_000
    max_input_tokens: int | None = None
    reserved_output_tokens: int = 0

    def __post_init__(self) -> None:
        if not 0 < self.target_ms <= self.maximum_ms:
            raise ValueError("target_ms must be positive and no larger than maximum_ms")
        if not 0 <= self.overlap_ms < self.target_ms:
            raise ValueError("overlap_ms must be non-negative and smaller than target_ms")
        if self.max_input_tokens is not None and self.max_input_tokens <= 0:
            raise ValueError("max_input_tokens must be positive when configured")
        if self.reserved_output_tokens < 0:
            raise ValueError("reserved_output_tokens must be non-negative")
        if self.max_input_tokens is not None and self.reserved_output_tokens >= self.max_input_tokens:
            raise ValueError("reserved_output_tokens must be smaller than max_input_tokens")


@dataclass(frozen=True, slots=True)
class SegmentManifest:
    chapters: tuple[Chapter, ...]
    topics: tuple[Topic, ...]


class BoundaryDetector(Protocol):
    def choose(self, transcript: Transcript, start_ms: int, target_ms: int, limit_ms: int) -> int: ...


class PausePunctuationBoundaryDetector:
    search_radius_ms = 60_000

    def choose(self, transcript: Transcript, start_ms: int, target_ms: int, limit_ms: int) -> int:
        lower = max(start_ms + 1, target_ms - self.search_radius_ms)
        upper = min(limit_ms, target_ms + self.search_radius_ms)
        candidates: list[tuple[float, int]] = []
        for index, segment in enumerate(transcript.segments):
            if not lower <= segment.end_ms <= upper:
                continue
            next_start = (
                transcript.segments[index + 1].start_ms if index + 1 < len(transcript.segments) else segment.end_ms
            )
            pause = min(30_000, max(0, next_start - segment.end_ms))
            punctuation = 30_000 if segment.text.rstrip().endswith((".", "?", "!", "다.")) else 0
            distance = abs(segment.end_ms - target_ms)
            candidates.append((punctuation + pause - distance * 0.25, segment.end_ms))
        return max(candidates)[1] if candidates else min(target_ms, limit_ms)


def _default_chapter(transcript: Transcript) -> Chapter:
    return Chapter(
        chapter_id="full-video",
        title="전체 영상",
        start_ms=0,
        end_ms=transcript.duration_ms,
    )


def _boundaries(
    transcript: Transcript,
    chapter: Chapter,
    policy: SegmentationPolicy,
    detector: BoundaryDetector,
) -> list[tuple[int, int]]:
    if chapter.end_ms - chapter.start_ms <= policy.maximum_ms:
        return [(chapter.start_ms, chapter.end_ms)]
    result: list[tuple[int, int]] = []
    start = chapter.start_ms
    while start < chapter.end_ms:
        target = min(start + policy.target_ms, chapter.end_ms)
        limit = min(start + policy.maximum_ms, chapter.end_ms)
        end = detector.choose(transcript, start, target, limit)
        if chapter.end_ms - end < policy.target_ms // 2:
            end = chapter.end_ms
        if end - start > policy.maximum_ms:
            end = start + policy.maximum_ms
        result.append((start, end))
        start = end
    return result


def _estimated_tokens(text: str) -> int:
    """Deterministic conservative estimate for segmentation, not provider billing."""
    words = len(text.split())
    non_whitespace = sum(not character.isspace() for character in text)
    return max(words, (non_whitespace + 2) // 3, 1)


def _apply_token_budget(
    transcript: Transcript,
    ranges: list[tuple[int, int]],
    policy: SegmentationPolicy,
) -> list[tuple[int, int]]:
    if policy.max_input_tokens is None:
        return ranges
    allowance = policy.max_input_tokens - policy.reserved_output_tokens
    bounded: list[tuple[int, int]] = []
    for start, end in ranges:
        indexes = [
            index
            for index, segment in enumerate(transcript.segments)
            if segment.end_ms > start and segment.start_ms < end
        ]
        if not indexes:
            bounded.append((start, end))
            continue
        current_start = start
        used = 0
        for index in indexes:
            segment = transcript.segments[index]
            estimate = _estimated_tokens(segment.text)
            if used and used + estimate > allowance:
                bounded.append((current_start, segment.start_ms))
                current_start = segment.start_ms
                used = 0
            used += estimate
        bounded.append((current_start, end))
    return bounded


def coalesce_chapters(chapters: tuple[Chapter, ...], duration_ms: int, depth: str = "detailed") -> tuple[Chapter, ...]:
    if not chapters:
        return ()
    if depth in ("brief", "short", "quick", "simple", "concise"):
        max_chapters = 3
    elif depth in ("deep", "심층", "꽉찬"):
        max_chapters = 15
    else:  # detailed
        if duration_ms <= 30 * 60_000:
            max_chapters = 5
        elif duration_ms <= 60 * 60_000:
            max_chapters = 8
        else:
            max_chapters = 12

    if len(chapters) <= max_chapters:
        return chapters

    group_size = (len(chapters) + max_chapters - 1) // max_chapters
    coalesced: list[Chapter] = []
    for i in range(0, len(chapters), group_size):
        chunk = chapters[i : i + group_size]
        title = chunk[0].title
        coalesced.append(
            Chapter(
                chapter_id=f"chapter-{len(coalesced) + 1:03d}",
                title=title,
                start_ms=chunk[0].start_ms,
                end_ms=chunk[-1].end_ms,
            )
        )
    return tuple(coalesced)


def segment_transcript(
    transcript: Transcript,
    chapters: tuple[Chapter, ...],
    policy: SegmentationPolicy,
    detector: BoundaryDetector | None = None,
    depth: str = "detailed",
) -> SegmentManifest:
    selected_detector = detector or PausePunctuationBoundaryDetector()
    selected_chapters = (
        coalesce_chapters(chapters, transcript.duration_ms, depth=depth)
        if chapters
        else (_default_chapter(transcript),)
    )
    topics: list[Topic] = []
    for chapter in selected_chapters:
        ranges = _apply_token_budget(
            transcript,
            _boundaries(transcript, chapter, policy, selected_detector),
            policy,
        )
        for position, (start, end) in enumerate(ranges, start=1):
            # Overlap is extra input. Omit it when enforcing a strict input budget.
            context_start = (
                start
                if position == 1 or policy.max_input_tokens is not None
                else max(chapter.start_ms, start - policy.overlap_ms)
            )
            indexes = tuple(
                index
                for index, segment in enumerate(transcript.segments)
                if segment.end_ms > context_start and segment.start_ms < end
            )
            title = chapter.title if len(ranges) == 1 else f"{chapter.title} · {position}"
            topics.append(
                Topic(
                    topic_id=f"{chapter.chapter_id}-topic-{position:03d}",
                    chapter_id=chapter.chapter_id,
                    title=title,
                    start_ms=start,
                    end_ms=end,
                    segment_indexes=indexes,
                )
            )
    return SegmentManifest(tuple(selected_chapters), tuple(topics))
