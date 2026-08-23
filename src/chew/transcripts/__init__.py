"""Transcript provider chain and built-in adapters."""

from chew.transcripts.base import TranscriptProvider
from chew.transcripts.pytubefix import PytubeFixTranscriptProvider
from chew.transcripts.service import TranscriptService
from chew.transcripts.whisper import WhisperProvider
from chew.transcripts.youtube_api import YouTubeApiTranscriptProvider
from chew.transcripts.youtube_timedtext import YouTubeTimedTextProvider
from chew.transcripts.youtubei import YouTubeiTranscriptProvider
from chew.transcripts.yt_dlp import YtDlpSubtitleProvider


def default_providers(
    *, whisper: bool = False, cookie_file: str | None = None, browser_profile: tuple[str, str] | None = None
) -> tuple[TranscriptProvider, ...]:
    providers: list[TranscriptProvider] = [
        YouTubeiTranscriptProvider(),
        YouTubeTimedTextProvider(),
        YtDlpSubtitleProvider(caption_kind="manual", cookie_file=cookie_file, browser_profile=browser_profile),
        YtDlpSubtitleProvider(caption_kind="automatic", cookie_file=cookie_file, browser_profile=browser_profile),
        YouTubeApiTranscriptProvider(),
        PytubeFixTranscriptProvider(),
    ]
    if whisper:
        providers.append(WhisperProvider())
    return tuple(providers)


__all__ = ["TranscriptService", "default_providers"]
