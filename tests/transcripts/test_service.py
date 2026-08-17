import pytest

from chew.domain import Provenance, SourceIdentity, Transcript, TranscriptSegment
from chew.identity import normalize_source
from chew.transcripts.base import TranscriptProvider
from chew.transcripts.service import TranscriptService, TranscriptUnavailable

SOURCE = SourceIdentity(
    source_id="youtube:abcDEF_1234",
    video_id="abcDEF_1234",
    canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
)


class StubProvider:
    def __init__(self, name: str, result: Transcript | None) -> None:
        self.name = name
        self.result = result
        self.calls = 0

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None:
        self.calls += 1
        return self.result


def candidate(end_ms: int) -> Transcript:
    return Transcript(
        source=SOURCE,
        language="ko",
        duration_ms=10_000,
        provenance=Provenance.AUTO_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=end_ms, text="충분한 자막"),),
    )


@pytest.mark.asyncio
async def test_service_skips_rejected_candidate_and_uses_next_provider() -> None:
    weak = StubProvider("weak", candidate(1_000))
    good = StubProvider("good", candidate(9_000))

    resolution = await TranscriptService([weak, good]).resolve(SOURCE, "ko")

    assert resolution.provider == "good"
    assert [attempt.provider for attempt in resolution.attempts] == ["weak"]
    assert weak.calls == good.calls == 1


@pytest.mark.asyncio
async def test_service_records_all_failures() -> None:
    providers: list[TranscriptProvider] = [
        StubProvider("missing", None),
        StubProvider("weak", candidate(1_000)),
    ]

    with pytest.raises(TranscriptUnavailable) as captured:
        await TranscriptService(providers).resolve(SOURCE, "ko")

    assert [attempt.provider for attempt in captured.value.attempts] == ["missing", "weak"]


@pytest.mark.asyncio
async def test_optional_provider_runs_only_when_explicitly_enabled() -> None:
    regular = StubProvider("regular", None)
    optional = StubProvider("faster-whisper", candidate(10_000))
    service = TranscriptService([regular], optional_providers=[optional])

    with pytest.raises(TranscriptUnavailable):
        await service.resolve(SOURCE, "ko")
    assert optional.calls == 0

    resolution = await service.resolve(SOURCE, "ko", include_optional=True)
    assert resolution.provider == "faster-whisper"
    assert optional.calls == 1


@pytest.mark.asyncio
async def test_local_media_uses_only_the_dedicated_local_provider(tmp_path) -> None:  # type: ignore[no-untyped-def]
    media = tmp_path / "meeting.wav"
    media.write_bytes(b"audio")
    source = normalize_source(str(media))

    class UnexpectedYouTubeProvider:
        name = "youtube"

        async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None:
            raise AssertionError("YouTube providers must not receive local media")

    local = StubProvider(
        "local-whisper",
        candidate(10_000).model_copy(update={"source": source, "language": "ko"}),
    )
    service = TranscriptService(
        [UnexpectedYouTubeProvider()],
        local_providers=[local],
    )

    resolution = await service.resolve(source, "ko")

    assert resolution.provider == "local-whisper"
    assert local.calls == 1
