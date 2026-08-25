from __future__ import annotations

import json

import pytest

from chew.domain import Provenance
from chew.identity import normalize_youtube_url
from chew.transcripts.youtube_timedtext import YouTubeTimedTextProvider

SOURCE = normalize_youtube_url("https://youtu.be/abcDEF_1234")
pytestmark = pytest.mark.asyncio


async def test_provider_reads_caption_track_from_player_response() -> None:
    player_response = {
        "videoDetails": {"title": "영상 제목", "lengthSeconds": "12"},
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {
                        "baseUrl": "https://captions.example/manual-en",
                        "languageCode": "en",
                        "name": {"simpleText": "English"},
                    },
                    {
                        "baseUrl": "https://captions.example/automatic-en",
                        "languageCode": "en",
                        "name": {"simpleText": "English (auto)"},
                        "kind": "asr",
                    },
                ]
            }
        },
    }
    requested_urls: list[str] = []

    def load_player(_: str) -> str:
        return f"var ytInitialPlayerResponse = {json.dumps(player_response)};"

    def load_track(url: str) -> str:
        requested_urls.append(url)
        return "WEBVTT\n\n00:00:00.000 --> 00:00:06.000\nfirst caption\n\n00:00:06.000 --> 00:00:12.000\nsecond caption\n"

    provider = YouTubeTimedTextProvider(player_loader=load_player, track_loader=load_track)

    transcript = await provider.fetch(SOURCE, "en")

    assert transcript is not None
    assert transcript.title == "영상 제목"
    assert transcript.duration_ms == 12_000
    assert transcript.provenance == Provenance.MANUAL_SUBTITLE
    assert [segment.text for segment in transcript.segments] == ["first caption", "second caption"]
    assert requested_urls == ["https://captions.example/manual-en?fmt=vtt"]


async def test_provider_uses_automatic_track_when_no_manual_track_exists() -> None:
    player_response = {
        "videoDetails": {"title": "자동 자막 영상", "lengthSeconds": "5"},
        "captions": {
            "playerCaptionsTracklistRenderer": {
                "captionTracks": [
                    {"baseUrl": "https://captions.example/automatic-ko", "languageCode": "ko", "kind": "asr"}
                ]
            }
        },
    }
    provider = YouTubeTimedTextProvider(
        player_loader=lambda _: f"ytInitialPlayerResponse = {json.dumps(player_response)};",
        track_loader=lambda _: "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n자동 자막\n",
    )

    transcript = await provider.fetch(SOURCE, "ko")

    assert transcript is not None
    assert transcript.provenance == Provenance.AUTO_SUBTITLE
    assert transcript.language == "ko"
