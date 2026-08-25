from pathlib import Path

import pytest

from chew.domain import Provenance, SourceIdentity
from chew.transcripts.user_input import UserTranscriptInputError, UserTranscriptProvider

SOURCE = SourceIdentity(
    source_id="youtube:abcDEF_1234",
    video_id="abcDEF_1234",
    canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
)


@pytest.mark.asyncio
async def test_vtt_input_retains_caption_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "captions.vtt"
    path.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello", encoding="utf-8")

    transcript = await UserTranscriptProvider(path).fetch(SOURCE, "en")

    assert transcript.provenance is Provenance.USER_PROVIDED
    assert transcript.segments[0].start_ms == 1_000
    assert transcript.segments[0].end_ms == 3_000


@pytest.mark.asyncio
async def test_srt_input_retains_caption_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "captions.srt"
    path.write_text("1\n00:00:02,000 --> 00:00:04,000\nHello\n", encoding="utf-8")

    transcript = await UserTranscriptProvider(path).fetch(SOURCE, "en")

    assert transcript.segments[0].start_ms == 2_000


@pytest.mark.asyncio
async def test_text_input_assigns_deterministic_sequential_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "captions.txt"
    path.write_text("First line\n\nSecond line\n", encoding="utf-8")

    transcript = await UserTranscriptProvider(path).fetch(SOURCE, "en")

    assert [(item.start_ms, item.end_ms, item.text) for item in transcript.segments] == [
        (0, 30_000, "First line"),
        (30_000, 60_000, "Second line"),
    ]


@pytest.mark.asyncio
async def test_empty_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "captions.txt"
    path.write_text("\n", encoding="utf-8")

    with pytest.raises(UserTranscriptInputError, match="empty"):
        await UserTranscriptProvider(path).fetch(SOURCE, "en")


@pytest.mark.asyncio
async def test_unknown_file_format_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "captions.md"
    path.write_text("content", encoding="utf-8")

    with pytest.raises(UserTranscriptInputError, match="VTT, SRT, or TXT"):
        await UserTranscriptProvider(path).fetch(SOURCE, "en")
