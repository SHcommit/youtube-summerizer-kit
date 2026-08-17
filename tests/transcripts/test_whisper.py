from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from chew.domain import Provenance
from chew.identity import normalize_source, normalize_youtube_url
from chew.transcripts.whisper import WhisperDependencyMissing, WhisperProvider

pytestmark = pytest.mark.asyncio


@dataclass
class Segment:
    start: float
    end: float
    text: str


class Model:
    def transcribe(self, audio: str, **_: object) -> tuple[list[Segment], object]:
        assert Path(audio).exists()
        return [Segment(0, 4, "음성 인식")], object()


async def test_audio_is_removed_after_transcription(tmp_path: Path) -> None:
    observed: list[Path] = []

    def download(_: str, destination: Path) -> Path:
        path = destination / "audio.m4a"
        path.write_bytes(b"audio")
        observed.append(path)
        return path

    source = normalize_youtube_url("https://youtu.be/abcDEF_1234")
    result = await WhisperProvider(
        audio_downloader=download,
        model_factory=lambda *_: Model(),
        temporary_root=tmp_path,
    ).fetch(source, "ko")
    assert result is not None
    assert result.provenance == Provenance.WHISPER
    assert not observed[0].exists()


async def test_missing_optional_dependency_has_install_hint() -> None:
    provider = WhisperProvider(model_factory=None)
    with pytest.raises(WhisperDependencyMissing, match=r"whisper"):
        await provider.fetch(normalize_youtube_url("https://youtu.be/abcDEF_1234"), "ko")


async def test_local_media_is_transcribed_in_place_without_downloading_or_deleting(
    tmp_path: Path,
) -> None:
    media = tmp_path / "meeting.mp4"
    media.write_bytes(b"original local media")
    observed: list[Path] = []

    class RecordingModel:
        def transcribe(self, audio: str, **_: object) -> tuple[list[Segment], object]:
            observed.append(Path(audio))
            return [Segment(0, 4, "local transcript")], object()

    def unexpected_download(_: str, destination: Path) -> Path:
        raise AssertionError(f"local media must not be downloaded into {destination}")

    result = await WhisperProvider(
        audio_downloader=unexpected_download,
        model_factory=lambda *_: RecordingModel(),
    ).fetch(normalize_source(str(media)), "en")

    assert result is not None
    assert observed == [media.resolve()]
    assert result.title == "meeting"
    assert media.read_bytes() == b"original local media"
