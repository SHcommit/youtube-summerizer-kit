"""Fallback adapter for youtube-transcript-api."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from contextvars import ContextVar
from importlib import import_module
from typing import Any

from ytsum.domain import Provenance, SourceIdentity, Transcript, TranscriptSegment


def _default_api() -> Any:
    try:
        api_type = import_module("youtube_transcript_api").YouTubeTranscriptApi
    except ImportError as error:
        raise RuntimeError(
            "youtube-transcript-api가 필요합니다: pip install youtube-summarizer-kit[youtube]"
        ) from error
    return api_type()


def _value(item: object, name: str) -> Any:
    if isinstance(item, dict):
        return item[name]
    return getattr(item, name)


class YouTubeApiTranscriptProvider:
    name = "youtube-transcript-api"

    def __init__(self, api_factory: Callable[[], Any] = _default_api) -> None:
        self.api_factory = api_factory
        self._attempt_failure: ContextVar[tuple[str, ...]] = ContextVar(
            f"ytsum_youtube_api_failure_{id(self)}", default=()
        )

    def attempt_reasons(self) -> tuple[str, ...]:
        return self._attempt_failure.get()

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None:
        self._attempt_failure.set(())
        try:
            api = self.api_factory()
            try:
                fetched: Iterable[object] = await asyncio.to_thread(
                    api.fetch, source.video_id, languages=[language]
                )
            except Exception:
                langs = [lang for lang in ("en", "ko", "ja") if lang != language]
                fetched = await asyncio.to_thread(
                    api.fetch, source.video_id, languages=langs
                )
            segments = tuple(
                TranscriptSegment(
                    start_ms=round(float(_value(item, "start")) * 1_000),
                    end_ms=round(
                        (float(_value(item, "start")) + float(_value(item, "duration"))) * 1_000
                    ),
                    text=str(_value(item, "text")).strip(),
                )
                for item in fetched
                if str(_value(item, "text")).strip()
            )
            if not segments:
                return None
            return Transcript(
                source=source,
                language=language,
                duration_ms=max(segment.end_ms for segment in segments),
                provenance=Provenance.TRANSCRIPT_API,
                segments=segments,
            )
        except Exception as error:
            self._attempt_failure.set((f"provider_error:{type(error).__name__}",))
            return None
