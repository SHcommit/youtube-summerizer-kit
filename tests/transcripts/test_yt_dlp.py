from __future__ import annotations

import pytest

from chew.domain import Provenance
from chew.identity import normalize_youtube_url
from chew.transcripts.yt_dlp import YtDlpSubtitleProvider

SOURCE = normalize_youtube_url("https://youtu.be/abcDEF_1234")
pytestmark = pytest.mark.asyncio


async def test_manual_subtitles_are_preferred_over_automatic() -> None:
    info = {
        "duration": 10.0,
        "title": "실제 영상 제목",
        "chapters": [{"title": "도입", "start_time": 0.0, "end_time": 10.0}],
        "subtitles": {"ko": [{"data": "WEBVTT\n\n00:00.000 --> 00:10.000\n수동"}]},
        "automatic_captions": {"ko": [{"data": "WEBVTT\n\n00:00.000 --> 00:10.000\n자동"}]},
    }
    provider = YtDlpSubtitleProvider(extractor=lambda _: info)
    transcript = await provider.fetch(SOURCE, "ko")
    assert transcript is not None
    assert transcript.provenance == Provenance.MANUAL_SUBTITLE
    assert transcript.segments[0].text == "수동"
    assert transcript.title == "실제 영상 제목"
    assert transcript.chapters[0].title == "도입"


async def test_provider_failure_allows_fallback() -> None:
    def broken(_: str) -> dict[str, object]:
        raise RuntimeError("network")

    assert await YtDlpSubtitleProvider(extractor=broken).fetch(SOURCE, "ko") is None


async def test_provider_failure_reason_is_recorded_by_fallback_service() -> None:
    from chew.transcripts.service import TranscriptService, TranscriptUnavailable

    def broken(_: str) -> dict[str, object]:
        raise RuntimeError("network")

    with pytest.raises(TranscriptUnavailable) as captured:
        await TranscriptService(
            [YtDlpSubtitleProvider(extractor=broken, caption_kind="manual")]
        ).resolve(SOURCE, "ko")

    assert captured.value.attempts[0].reasons == ("provider_error:RuntimeError",)


async def test_manual_and_automatic_can_be_independent_fallback_candidates() -> None:
    info = {
        "duration": 10.0,
        "subtitles": {"ko": [{"data": "WEBVTT\n\n00:00.000 --> 00:01.000\n짧음"}]},
        "automatic_captions": {
            "ko": [{"data": "WEBVTT\n\n00:00.000 --> 00:10.000\n전체 자동 자막"}]
        },
    }
    from chew.transcripts.service import TranscriptService

    resolution = await TranscriptService(
        [
            YtDlpSubtitleProvider(extractor=lambda _: info, caption_kind="manual"),
            YtDlpSubtitleProvider(extractor=lambda _: info, caption_kind="automatic"),
        ]
    ).resolve(SOURCE, "ko")
    assert resolution.transcript.provenance == Provenance.AUTO_SUBTITLE
    assert resolution.attempts[0].provider == "yt-dlp-manual"


async def test_metadata_survives_when_yt_dlp_has_no_usable_subtitle() -> None:
    from chew.domain import Transcript, TranscriptSegment
    from chew.transcripts.service import TranscriptService

    info = {
        "duration": 10.0,
        "title": "보존할 제목",
        "chapters": [{"title": "도입", "start_time": 0, "end_time": 10}],
    }

    class ApiProvider:
        name = "api"

        async def fetch(self, source, language):  # type: ignore[no-untyped-def]
            return Transcript(
                source=source,
                language=language,
                duration_ms=10_000,
                provenance=Provenance.TRANSCRIPT_API,
                segments=(TranscriptSegment(start_ms=0, end_ms=10_000, text="API 자막"),),
            )

    resolution = await TranscriptService(
        [YtDlpSubtitleProvider(extractor=lambda _: info), ApiProvider()]
    ).resolve(SOURCE, "ko")

    assert resolution.transcript.title == "보존할 제목"
    assert resolution.transcript.chapters[0].title == "도입"


async def test_metadata_survives_when_optional_whisper_is_used() -> None:
    from chew.domain import Transcript, TranscriptSegment
    from chew.transcripts.service import TranscriptService

    info = {
        "duration": 10.0,
        "title": "보존할 제목",
        "chapters": [{"title": "도입", "start_time": 0, "end_time": 10}],
    }

    class WhisperProvider:
        name = "faster-whisper"

        async def fetch(self, source, language):  # type: ignore[no-untyped-def]
            return Transcript(
                source=source,
                language=language,
                duration_ms=10_000,
                provenance=Provenance.WHISPER,
                segments=(TranscriptSegment(start_ms=0, end_ms=10_000, text="음성 인식"),),
            )

    resolution = await TranscriptService(
        [YtDlpSubtitleProvider(extractor=lambda _: info)],
        optional_providers=[WhisperProvider()],
    ).resolve(SOURCE, "ko", include_optional=True)

    assert resolution.transcript.title == "보존할 제목"
    assert resolution.transcript.chapters[0].title == "도입"


async def test_failed_next_video_cannot_reuse_previous_video_metadata() -> None:
    calls = 0

    def extractor(_: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"title": "첫 영상", "duration": 10}
        raise RuntimeError("second video unavailable")

    provider = YtDlpSubtitleProvider(extractor=extractor)
    assert await provider.fetch(SOURCE, "ko") is None
    assert provider.attempt_metadata()[0] == "첫 영상"

    other = SOURCE.model_copy(update={"source_id": "youtube:other", "video_id": "other"})
    assert await provider.fetch(other, "ko") is None
    assert provider.attempt_metadata() == (None, ())
