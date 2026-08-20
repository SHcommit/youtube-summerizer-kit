"""Optional local speech-to-text fallback using faster-whisper."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Callable, Iterable
from importlib import import_module
from pathlib import Path
from typing import Any, cast

from chew.domain import Provenance, SourceIdentity, SourceKind, Transcript, TranscriptSegment


class WhisperDependencyMissing(RuntimeError):
    pass


def _model(model_name: str) -> Any:
    try:
        model_type = import_module("faster_whisper").WhisperModel
    except ImportError as error:
        raise WhisperDependencyMissing(
            "Whisper 사용에는 `pip install youtube-summarizer-kit[whisper]`가 필요합니다."
        ) from error
    return model_type(model_name, device="auto", compute_type="int8")


def _download_audio(url: str, destination: Path) -> Path:
    try:
        youtube_dl = import_module("yt_dlp").YoutubeDL
    except ImportError as error:
        raise WhisperDependencyMissing(
            "Whisper 오디오 추출에는 `pip install youtube-summarizer-kit[youtube]`가 필요합니다."
        ) from error
    template = str(destination / "audio.%(ext)s")
    with youtube_dl(
        {"format": "m4a/bestaudio/best", "outtmpl": template, "quiet": True, "no_warnings": True}
    ) as downloader:
        info = downloader.extract_info(url, download=True)
        return Path(downloader.prepare_filename(info))


class WhisperProvider:
    name = "faster-whisper"

    def __init__(
        self,
        *,
        audio_downloader: Callable[[str, Path], Path] = _download_audio,
        model_factory: Callable[[str], Any] | None = None,
        model_name: str = "small",
        temporary_root: Path | None = None,
    ) -> None:
        self.audio_downloader = audio_downloader
        self.model_factory = model_factory
        self.model_name = model_name
        self.temporary_root = temporary_root

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None:
        factory = self.model_factory or _model
        model = await asyncio.to_thread(factory, self.model_name)

        async def transcribe_audio(audio: Path) -> Transcript | None:
            def transcribe() -> tuple[Iterable[Any], Any]:
                return cast(
                    tuple[Iterable[Any], Any],
                    model.transcribe(
                        str(audio),
                        language=language,
                        vad_filter=True,
                        condition_on_previous_text=False,
                    ),
                )

            generated, _ = await asyncio.to_thread(transcribe)
            items = await asyncio.to_thread(list, generated)
            segments = tuple(
                TranscriptSegment(
                    start_ms=round(float(item.start) * 1_000),
                    end_ms=round(float(item.end) * 1_000),
                    text=str(item.text).strip(),
                )
                for item in items
                if str(item.text).strip()
            )
            if not segments:
                return None
            return Transcript(
                source=source,
                language=language,
                duration_ms=max(segment.end_ms for segment in segments),
                provenance=Provenance.WHISPER,
                segments=segments,
                title=audio.stem if source.kind == SourceKind.LOCAL_MEDIA else None,
            )

        if source.kind == SourceKind.LOCAL_MEDIA:
            if source.local_path is None:
                raise RuntimeError("Expected local_path for LOCAL_MEDIA source but got None")
            return await transcribe_audio(Path(source.local_path))

        with tempfile.TemporaryDirectory(dir=self.temporary_root, prefix="chew-audio-") as raw:
            destination = Path(raw)
            audio = await asyncio.to_thread(self.audio_downloader, source.canonical_url, destination)
            return await transcribe_audio(audio)
