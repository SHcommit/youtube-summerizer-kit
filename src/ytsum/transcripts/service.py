"""Ordered fallback resolution for transcript providers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ytsum.domain import Chapter, SourceIdentity, SourceKind, Transcript
from ytsum.transcripts.base import TranscriptProvider
from ytsum.transcripts.validation import normalize_transcript, validate_transcript


@dataclass(frozen=True, slots=True)
class TranscriptAttempt:
    provider: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TranscriptResolution:
    transcript: Transcript
    provider: str
    attempts: tuple[TranscriptAttempt, ...]


class TranscriptUnavailable(RuntimeError):
    def __init__(self, attempts: tuple[TranscriptAttempt, ...]) -> None:
        super().__init__("사용 가능한 YouTube 자막을 찾지 못했습니다")
        self.attempts = attempts


class TranscriptService:
    def __init__(
        self,
        providers: Sequence[TranscriptProvider],
        *,
        optional_providers: Sequence[TranscriptProvider] = (),
        local_providers: Sequence[TranscriptProvider] = (),
    ) -> None:
        self.providers = providers
        self.optional_providers = optional_providers
        self.local_providers = local_providers

    async def resolve(
        self, source: SourceIdentity, language: str, *, include_optional: bool = False
    ) -> TranscriptResolution:
        attempts: list[TranscriptAttempt] = []
        metadata_title: str | None = None
        metadata_chapters: tuple[Chapter, ...] = ()
        if source.kind == SourceKind.LOCAL_MEDIA:
            providers = self.local_providers
        else:
            providers = (
                (*self.providers, *self.optional_providers) if include_optional else self.providers
            )
        for provider in providers:
            candidate = await provider.fetch(source, language)
            if candidate is None:
                attempt_metadata = getattr(provider, "attempt_metadata", None)
                if callable(attempt_metadata):
                    provider_title, provider_chapters = attempt_metadata()
                    metadata_title = metadata_title or provider_title
                    metadata_chapters = metadata_chapters or provider_chapters
                attempt_reasons = getattr(provider, "attempt_reasons", None)
                reasons = attempt_reasons() if callable(attempt_reasons) else ()
                attempts.append(TranscriptAttempt(provider.name, reasons or ("not_available",)))
                continue
            metadata_title = metadata_title or candidate.title
            metadata_chapters = metadata_chapters or candidate.chapters
            raw_report = validate_transcript(candidate)
            cand_base = candidate.language.split("-", 1)[0]
            req_base = language.split("-", 1)[0]
            language_matches = (cand_base == req_base) or (cand_base in ("ko", "en", "ja"))
            if not language_matches:
                attempts.append(TranscriptAttempt(provider.name, ("language_mismatch",)))
                continue
            if "timestamps_not_monotonic" in raw_report.reasons:
                attempts.append(TranscriptAttempt(provider.name, raw_report.reasons))
                continue
            normalized = normalize_transcript(candidate)
            report = validate_transcript(normalized)
            if report.accepted:
                normalized = normalized.model_copy(
                    update={
                        "title": normalized.title or metadata_title,
                        "chapters": normalized.chapters or metadata_chapters,
                    }
                )
                return TranscriptResolution(normalized, provider.name, tuple(attempts))
            attempts.append(TranscriptAttempt(provider.name, report.reasons))
        raise TranscriptUnavailable(tuple(attempts))
