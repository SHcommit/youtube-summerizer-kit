"""Local user-provided transcript input without browser or network access."""

from __future__ import annotations

import re
from pathlib import Path

from chew.domain import Provenance, SourceIdentity, Transcript, TranscriptSegment

_TIMING = re.compile(
    r"(?m)^(?:(?:\d+\s*\n)?)(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+"
    r"(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})[^\n]*\n(?P<text>.*?)(?=\n\s*\n|\Z)",
    re.DOTALL,
)


class UserTranscriptInputError(ValueError):
    """A user-provided transcript file cannot be parsed safely."""


def _milliseconds(value: str) -> int:
    seconds = 0.0
    for part in value.replace(",", ".").split(":"):
        seconds = seconds * 60 + float(part)
    return round(seconds * 1_000)


def _timestamped_segments(value: str) -> tuple[TranscriptSegment, ...]:
    segments: list[TranscriptSegment] = []
    for match in _TIMING.finditer(value):
        text = re.sub(r"<[^>]+>", "", " ".join(match.group("text").splitlines())).strip()
        if not text:
            continue
        segments.append(
            TranscriptSegment(
                start_ms=_milliseconds(match.group("start")),
                end_ms=_milliseconds(match.group("end")),
                text=text,
            )
        )
    return tuple(segments)


def _text_segments(value: str) -> tuple[TranscriptSegment, ...]:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    return tuple(
        TranscriptSegment(start_ms=index * 30_000, end_ms=(index + 1) * 30_000, text=line)
        for index, line in enumerate(lines)
    )


class UserTranscriptProvider:
    """Adapt a local VTT, SRT, or TXT file to the transcript provider port."""

    name = "user-provided-transcript"

    def __init__(self, path: Path) -> None:
        self.path = path

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript:
        suffix = self.path.suffix.casefold()
        if suffix not in {".vtt", ".srt", ".txt"}:
            raise UserTranscriptInputError("Transcript input must be a VTT, SRT, or TXT file")
        try:
            content = self.path.read_text(encoding="utf-8-sig")
        except OSError as error:
            raise UserTranscriptInputError(f"Cannot read transcript input: {self.path.name}") from error
        if not content.strip():
            raise UserTranscriptInputError("Transcript input is empty")
        segments = _text_segments(content) if suffix == ".txt" else _timestamped_segments(content)
        if not segments:
            raise UserTranscriptInputError("Transcript input has no usable caption cues")
        return Transcript(
            source=source,
            language=language,
            duration_ms=segments[-1].end_ms,
            provenance=Provenance.USER_PROVIDED,
            segments=segments,
            title=self.path.stem,
        )
