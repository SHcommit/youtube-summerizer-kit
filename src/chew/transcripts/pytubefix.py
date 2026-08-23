"""Optional caption fallback using pytubefix."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from importlib import import_module
from typing import Any

from chew.domain import Provenance, SourceIdentity, Transcript, TranscriptSegment
from chew.transcripts.base import provider_failure_reason


def _default_youtube(url: str) -> Any:
    try:
        youtube = import_module("pytubefix").YouTube
    except ImportError as error:
        raise RuntimeError("pytubefix is required: pip install youtube-summarizer-kit[youtube]") from error
    return youtube(url)


def _srt_segments(value: str) -> tuple[TranscriptSegment, ...]:
    pattern = re.compile(
        r"(?m)^\d+\s*\n(\d{2}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}[,.]\d{3})[^\n]*\n(.+?)(?=\n\s*\n|\Z)",
        re.DOTALL,
    )

    def millis(timestamp: str) -> int:
        hours, minutes, seconds = timestamp.replace(",", ".").split(":")
        return round((int(hours) * 3_600 + int(minutes) * 60 + float(seconds)) * 1_000)

    return tuple(
        TranscriptSegment(start_ms=millis(match.group(1)), end_ms=millis(match.group(2)), text=" ".join(match.group(3).split()))
        for match in pattern.finditer(value)
        if match.group(3).strip()
    )


class PytubeFixTranscriptProvider:
    name = "pytubefix-captions"

    def __init__(self, youtube_factory: Callable[[str], Any] = _default_youtube) -> None:
        self.youtube_factory = youtube_factory
        self._attempt_failure: ContextVar[tuple[str, ...]] = ContextVar(
            f"chew_pytubefix_failure_{id(self)}", default=()
        )

    def attempt_reasons(self) -> tuple[str, ...]:
        return self._attempt_failure.get()

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None:
        self._attempt_failure.set(())
        try:
            video = await asyncio.to_thread(self.youtube_factory, source.canonical_url)
            captions = getattr(video, "captions", {})
            if not isinstance(captions, Mapping):
                return None
            keys = (language, f"a.{language}", language.split("-", 1)[0], f"a.{language.split('-', 1)[0]}")
            track = next((captions[key] for key in keys if key in captions), None)
            if track is None:
                return None
            segments = _srt_segments(str(track.generate_srt_captions()))
            if not segments:
                return None
            return Transcript(
                source=source,
                language=language,
                duration_ms=max(round(float(getattr(video, "length", 0)) * 1_000), segments[-1].end_ms),
                provenance=Provenance.AUTO_SUBTITLE if any(key.startswith("a.") for key in keys if key in captions) else Provenance.MANUAL_SUBTITLE,
                segments=segments,
                title=str(getattr(video, "title", "")) or None,
            )
        except Exception as error:
            self._attempt_failure.set((provider_failure_reason(error),))
            return None
