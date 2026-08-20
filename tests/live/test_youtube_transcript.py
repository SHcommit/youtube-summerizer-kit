from __future__ import annotations

import os

import pytest

from chew.identity import normalize_youtube_url
from chew.transcripts import TranscriptService, default_providers


@pytest.mark.asyncio
async def test_live_youtube_transcript_chain() -> None:
    url = os.environ.get("YTSUM_LIVE_YOUTUBE_URL")
    if not url:
        pytest.skip("set YTSUM_LIVE_YOUTUBE_URL to enable the live transcript test")
    resolution = await TranscriptService(default_providers()).resolve(normalize_youtube_url(url), "ko")
    assert resolution.transcript.segments
