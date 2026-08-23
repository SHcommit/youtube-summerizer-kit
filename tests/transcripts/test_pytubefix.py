from __future__ import annotations

import pytest

from chew.domain import Provenance
from chew.identity import normalize_youtube_url
from chew.transcripts.pytubefix import PytubeFixTranscriptProvider


class Caption:
    def generate_srt_captions(self) -> str:
        return "1\n00:00:00,000 --> 00:00:05,000\nAuto caption\n"


class Video:
    def __init__(self) -> None:
        self.title = "Fixture"
        self.length = 5
        self.captions = {"a.en": Caption()}


@pytest.mark.asyncio
async def test_pytubefix_uses_automatic_caption_track() -> None:
    source = normalize_youtube_url("https://youtu.be/abcDEF_1234")
    transcript = await PytubeFixTranscriptProvider(youtube_factory=lambda _: Video()).fetch(source, "en")

    assert transcript is not None
    assert transcript.provenance == Provenance.AUTO_SUBTITLE
    assert transcript.title == "Fixture"
    assert transcript.segments[0].text == "Auto caption"
