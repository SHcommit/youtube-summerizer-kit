"""Direct caption-track extraction from a public YouTube watch response."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from typing import Any, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from chew.domain import Provenance, SourceIdentity, Transcript, TranscriptSegment
from chew.transcripts.base import provider_failure_reason

PageLoader = Callable[[str], str]
TrackLoader = Callable[[str], str]

_PLAYER_RESPONSE_MARKER = re.compile(r"ytInitialPlayerResponse\s*=\s*")


def _read_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        },
    )
    with urlopen(request, timeout=20) as response:
        return cast(bytes, response.read()).decode("utf-8")


def _json_after_marker(page: str) -> Mapping[str, Any] | None:
    match = _PLAYER_RESPONSE_MARKER.search(page)
    if match is None:
        return None
    start = match.end()
    while start < len(page) and page[start].isspace():
        start += 1
    if start >= len(page) or page[start] != "{":
        return None

    depth = 0
    quoted = False
    escaped = False
    for end in range(start, len(page)):
        character = page[end]
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
            continue
        if character == '"':
            quoted = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                value = json.loads(page[start : end + 1])
                return value if isinstance(value, Mapping) else None
    return None


def _as_vtt_url(url: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["fmt"] = "vtt"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _seconds(value: str) -> float:
    result = 0.0
    for piece in value.replace(",", ".").split(":"):
        result = result * 60 + float(piece)
    return result


def _parse_vtt(value: str) -> list[TranscriptSegment]:
    pattern = re.compile(
        r"(?m)^(\d{1,2}:)?\d{2}:\d{2}[.,]\d{3}\s+-->\s+"
        r"((?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})[^\n]*\n(.+?)(?=\n\s*\n|\Z)",
        re.DOTALL,
    )
    segments: list[TranscriptSegment] = []
    for match in pattern.finditer(value):
        timing = match.group(0).splitlines()[0].split(" --> ")
        text = re.sub(r"<[^>]+>", "", " ".join(match.group(3).splitlines())).strip()
        if text:
            segments.append(
                TranscriptSegment(
                    start_ms=round(_seconds(timing[0]) * 1_000),
                    end_ms=round(_seconds(timing[1].split()[0]) * 1_000),
                    text=text,
                )
            )
    return segments


def _caption_tracks(player_response: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    captions = player_response.get("captions")
    if not isinstance(captions, Mapping):
        return []
    renderer = captions.get("playerCaptionsTracklistRenderer")
    if not isinstance(renderer, Mapping):
        return []
    tracks = renderer.get("captionTracks")
    return [track for track in tracks if isinstance(track, Mapping)] if isinstance(tracks, list) else []


def _pick_track(tracks: list[Mapping[str, Any]], language: str) -> Mapping[str, Any] | None:
    requested_base = language.split("-", 1)[0]

    def score(track: Mapping[str, Any]) -> tuple[int, int]:
        track_language = str(track.get("languageCode") or "")
        same_language = track_language == language
        same_base = track_language.split("-", 1)[0] == requested_base
        supported_fallback = track_language.split("-", 1)[0] in {"ko", "en", "ja"}
        language_score = 3 if same_language else 2 if same_base else 1 if supported_fallback else 0
        manual_score = 1 if track.get("kind") != "asr" else 0
        return language_score, manual_score

    usable = [track for track in tracks if isinstance(track.get("baseUrl"), str)]
    return max(usable, key=score, default=None)


class YouTubeTimedTextProvider:
    """Read public captionTracks and retrieve the selected timed-text track."""

    name = "youtube-timedtext"

    def __init__(
        self,
        *,
        player_loader: PageLoader = _read_text,
        track_loader: TrackLoader = _read_text,
    ) -> None:
        self.player_loader = player_loader
        self.track_loader = track_loader
        self._attempt_failure: ContextVar[tuple[str, ...]] = ContextVar(
            f"chew_timedtext_failure_{id(self)}", default=()
        )

    def attempt_reasons(self) -> tuple[str, ...]:
        return self._attempt_failure.get()

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None:
        self._attempt_failure.set(())
        try:
            player_response = _json_after_marker(await asyncio.to_thread(self.player_loader, source.canonical_url))
            if player_response is None:
                return None
            track = _pick_track(_caption_tracks(player_response), language)
            if track is None:
                return None
            raw_vtt = await asyncio.to_thread(self.track_loader, _as_vtt_url(str(track["baseUrl"])))
            segments = _parse_vtt(raw_vtt)
            if not segments:
                return None
            details = player_response.get("videoDetails")
            details = details if isinstance(details, Mapping) else {}
            duration_seconds = float(details.get("lengthSeconds") or 0)
            return Transcript(
                source=source,
                language=str(track.get("languageCode") or language),
                duration_ms=max(round(duration_seconds * 1_000), segments[-1].end_ms),
                provenance=Provenance.AUTO_SUBTITLE if track.get("kind") == "asr" else Provenance.MANUAL_SUBTITLE,
                segments=tuple(segments),
                title=str(details.get("title") or "") or None,
            )
        except Exception as error:  # Provider failures are recorded by the fallback chain.
            self._attempt_failure.set((provider_failure_reason(error),))
            return None
