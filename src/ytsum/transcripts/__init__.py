"""Transcript provider chain and built-in adapters."""

from ytsum.transcripts.base import TranscriptProvider
from ytsum.transcripts.service import TranscriptService
from ytsum.transcripts.whisper import WhisperProvider
from ytsum.transcripts.youtube_api import YouTubeApiTranscriptProvider
from ytsum.transcripts.yt_dlp import YtDlpSubtitleProvider


def default_providers(*, whisper: bool = False) -> tuple[TranscriptProvider, ...]:
    providers: list[TranscriptProvider] = [
        YtDlpSubtitleProvider(caption_kind="manual"),
        YtDlpSubtitleProvider(caption_kind="automatic"),
        YouTubeApiTranscriptProvider(),
    ]
    if whisper:
        providers.append(WhisperProvider())
    return tuple(providers)


__all__ = ["TranscriptService", "default_providers"]
