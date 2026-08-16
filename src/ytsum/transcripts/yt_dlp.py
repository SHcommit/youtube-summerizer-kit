"""Subtitle extraction through the embedded yt-dlp Python API."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from importlib import import_module
from typing import Any, Literal, cast
from urllib.request import urlopen

from ytsum.domain import Chapter, Provenance, SourceIdentity, Transcript, TranscriptSegment

Extractor = Callable[[str], Mapping[str, Any]]


def _default_extract(url: str) -> Mapping[str, Any]:
    try:
        youtube_dl = import_module("yt_dlp").YoutubeDL
    except ImportError as error:
        raise RuntimeError(
            "yt-dlp가 필요합니다: pip install youtube-summarizer-kit[youtube]"
        ) from error
    options = {"quiet": True, "no_warnings": True, "skip_download": True}
    with youtube_dl(options) as downloader:
        value = downloader.extract_info(url, download=False)
        return cast(Mapping[str, Any], downloader.sanitize_info(value))


def _seconds(value: str) -> float:
    pieces = value.replace(",", ".").split(":")
    result = 0.0
    for piece in pieces:
        result = result * 60 + float(piece)
    return result


def _parse_vtt(value: str) -> list[TranscriptSegment]:
    pattern = re.compile(
        r"(?m)^(\d{1,2}:)?\d{2}:\d{2}[.,]\d{3}\s+-->\s+"
        r"((?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})[^\n]*\n(.+?)(?=\n\s*\n|\Z)",
        re.DOTALL,
    )
    results: list[TranscriptSegment] = []
    for match in pattern.finditer(value):
        timing = match.group(0).splitlines()[0].split(" --> ")
        text = re.sub(r"<[^>]+>", "", " ".join(match.group(3).splitlines())).strip()
        if text:
            results.append(
                TranscriptSegment(
                    start_ms=round(_seconds(timing[0]) * 1_000),
                    end_ms=round(_seconds(timing[1].split()[0]) * 1_000),
                    text=text,
                )
            )
    return results


def _parse_json3(value: str) -> list[TranscriptSegment]:
    payload = json.loads(value)
    results = []
    for event in payload.get("events", []):
        text = "".join(segment.get("utf8", "") for segment in event.get("segs", [])).strip()
        start = int(event.get("tStartMs", 0))
        duration = max(1, int(event.get("dDurationMs", 1)))
        if text:
            results.append(TranscriptSegment(start_ms=start, end_ms=start + duration, text=text))
    return results


def _read_track(track: Mapping[str, Any]) -> str:
    embedded = track.get("data")
    if isinstance(embedded, str):
        return embedded
    url = track.get("url")
    if not isinstance(url, str):
        raise ValueError("subtitle track has neither data nor URL")
    with urlopen(url, timeout=20) as response:
        return cast(bytes, response.read()).decode("utf-8")


def _select_language(captions: Mapping[str, Any], language: str) -> list[Mapping[str, Any]]:
    keys = (language, language.split("-", 1)[0])
    for key in keys:
        tracks = captions.get(key)
        if isinstance(tracks, list):
            return [track for track in tracks if isinstance(track, Mapping)]
    for key, tracks in captions.items():
        if str(key).split("-", 1)[0] == keys[-1] and isinstance(tracks, list):
            return [track for track in tracks if isinstance(track, Mapping)]
    return []


def _chapters(info: Mapping[str, Any]) -> tuple[Chapter, ...]:
    values: list[Chapter] = []
    raw_chapters = info.get("chapters")
    if isinstance(raw_chapters, list):
        for index, chapter in enumerate(raw_chapters):
            if not isinstance(chapter, Mapping):
                continue
            start = round(float(chapter.get("start_time") or 0) * 1_000)
            end = round(float(chapter.get("end_time") or 0) * 1_000)
            if end > start:
                values.append(
                    Chapter(
                        chapter_id=f"youtube-{index + 1:03d}",
                        title=str(chapter.get("title") or f"Chapter {index + 1}"),
                        start_ms=start,
                        end_ms=end,
                    )
                )
    return tuple(values)


class YtDlpSubtitleProvider:
    def __init__(
        self,
        extractor: Extractor = _default_extract,
        *,
        caption_kind: Literal["manual", "automatic", "both"] = "both",
    ) -> None:
        self.extractor = extractor
        self.caption_kind = caption_kind
        self.name = f"yt-dlp-{caption_kind}"
        self._attempt_metadata: ContextVar[tuple[str | None, tuple[Chapter, ...]]] = ContextVar(
            f"ytsum_metadata_{id(self)}", default=(None, ())
        )
        self._attempt_failure: ContextVar[tuple[str, ...]] = ContextVar(
            f"ytsum_failure_{id(self)}", default=()
        )

    def attempt_metadata(self) -> tuple[str | None, tuple[Chapter, ...]]:
        return self._attempt_metadata.get()

    def attempt_reasons(self) -> tuple[str, ...]:
        return self._attempt_failure.get()

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None:
        self._attempt_metadata.set((None, ()))
        self._attempt_failure.set(())
        try:
            info = await asyncio.to_thread(self.extractor, source.canonical_url)
            title = str(info["title"]) if info.get("title") else None
            chapters = _chapters(info)
            self._attempt_metadata.set((title, chapters))
            candidates: tuple[tuple[str, Provenance], ...] = (
                ("subtitles", Provenance.MANUAL_SUBTITLE),
                ("automatic_captions", Provenance.AUTO_SUBTITLE),
            )
            if self.caption_kind == "manual":
                candidates = candidates[:1]
            elif self.caption_kind == "automatic":
                candidates = candidates[1:]
            for key, provenance in candidates:
                captions = info.get(key)
                if not isinstance(captions, Mapping):
                    continue
                tracks = _select_language(captions, language)
                if not tracks:
                    continue
                preferred = next(
                    (track for track in tracks if track.get("ext") in {"json3", "vtt"}),
                    tracks[0],
                )
                raw = await asyncio.to_thread(_read_track, preferred)
                segments = _parse_json3(raw) if preferred.get("ext") == "json3" else _parse_vtt(raw)
                if not segments:
                    continue
                duration_ms = max(
                    round(float(info.get("duration") or 0) * 1_000),
                    segments[-1].end_ms,
                )
                return Transcript(
                    source=source,
                    language=language,
                    duration_ms=duration_ms,
                    provenance=provenance,
                    segments=tuple(segments),
                    title=title,
                    chapters=chapters,
                )
        except Exception as error:  # Provider failures are recorded by the fallback chain.
            self._attempt_failure.set((f"provider_error:{type(error).__name__}",))
            return None
        return None
