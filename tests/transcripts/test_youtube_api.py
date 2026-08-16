from __future__ import annotations

from dataclasses import dataclass

import pytest

from ytsum.domain import Provenance
from ytsum.identity import normalize_youtube_url
from ytsum.transcripts.youtube_api import YouTubeApiTranscriptProvider

pytestmark = pytest.mark.asyncio


@dataclass
class Snippet:
    text: str
    start: float
    duration: float


class Api:
    def fetch(self, video_id: str, languages: list[str]) -> list[Snippet]:
        assert video_id == "abcDEF_1234"
        assert languages == ["ko"]
        return [Snippet("첫 문장", 0.0, 2.5), Snippet("둘째 문장", 2.5, 2.5)]


async def test_current_api_fetch_result_is_converted() -> None:
    source = normalize_youtube_url("https://youtu.be/abcDEF_1234")
    result = await YouTubeApiTranscriptProvider(api_factory=Api).fetch(source, "ko")
    assert result is not None
    assert result.duration_ms == 5_000
    assert result.provenance == Provenance.TRANSCRIPT_API
    assert [segment.text for segment in result.segments] == ["첫 문장", "둘째 문장"]


async def test_api_failure_reason_is_available_to_fallback_service() -> None:
    from ytsum.transcripts.service import TranscriptService, TranscriptUnavailable

    class BrokenApi:
        def fetch(self, video_id: str, languages: list[str]) -> list[Snippet]:
            raise ConnectionError("offline")

    source = normalize_youtube_url("https://youtu.be/abcDEF_1234")
    with pytest.raises(TranscriptUnavailable) as captured:
        await TranscriptService([YouTubeApiTranscriptProvider(api_factory=BrokenApi)]).resolve(
            source, "ko"
        )

    assert captured.value.attempts[0].reasons == ("provider_error:ConnectionError",)
