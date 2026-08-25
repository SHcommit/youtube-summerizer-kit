"""Transcript provider chain and built-in adapters."""

from chew.transcripts.base import TranscriptProvider
from chew.transcripts.pytubefix import PytubeFixTranscriptProvider
from chew.transcripts.service import TranscriptService
from chew.transcripts.user_input import UserTranscriptInputError, UserTranscriptProvider
from chew.transcripts.whisper import WhisperProvider
from chew.transcripts.youtube_api import YouTubeApiTranscriptProvider
from chew.transcripts.youtube_timedtext import YouTubeTimedTextProvider
from chew.transcripts.youtubei import YouTubeiTranscriptProvider
from chew.transcripts.yt_dlp import YtDlpSubtitleProvider


def default_providers(*, whisper: bool = False) -> tuple[TranscriptProvider, ...]:
    providers: list[TranscriptProvider] = [
        YouTubeiTranscriptProvider(),
        YouTubeTimedTextProvider(),
        YtDlpSubtitleProvider(caption_kind="manual"),
        YtDlpSubtitleProvider(caption_kind="automatic"),
        YouTubeApiTranscriptProvider(),
        PytubeFixTranscriptProvider(),
    ]
    if whisper:
        providers.append(WhisperProvider())
    return tuple(providers)


__all__ = ["TranscriptService", "UserTranscriptInputError", "UserTranscriptProvider", "default_providers"]
