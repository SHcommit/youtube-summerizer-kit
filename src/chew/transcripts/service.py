"""Ordered fallback resolution for transcript providers."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass

from chew.domain import Chapter, SourceIdentity, SourceKind, Transcript
from chew.transcripts.base import TranscriptProvider
from chew.transcripts.validation import normalize_transcript, validate_transcript


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


class TranscriptRateLimited(TranscriptUnavailable):
    """All viable caption providers were rate-limited after bounded retries."""

    def __init__(self, attempts: tuple[TranscriptAttempt, ...], retry_after_seconds: int) -> None:
        super().__init__(attempts)
        self.retry_after_seconds = retry_after_seconds


class TranscriptService:
    def __init__(
        self,
        providers: Sequence[TranscriptProvider],
        *,
        optional_providers: Sequence[TranscriptProvider] = (),
        local_providers: Sequence[TranscriptProvider] = (),
        rate_limit_retries: int = 1,
        retry_delay_seconds: float = 1.0,
        provider_timeout_seconds: float = 20.0,
        acquisition_timeout_seconds: float = 60.0,
    ) -> None:
        if rate_limit_retries < 0:
            raise ValueError("rate_limit_retries must not be negative")
        if provider_timeout_seconds <= 0:
            raise ValueError("provider_timeout_seconds must be positive")
        if acquisition_timeout_seconds <= 0:
            raise ValueError("acquisition_timeout_seconds must be positive")
        self.providers = providers
        self.optional_providers = optional_providers
        self.local_providers = local_providers
        self.rate_limit_retries = rate_limit_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.provider_timeout_seconds = provider_timeout_seconds
        self.acquisition_timeout_seconds = acquisition_timeout_seconds

    async def resolve(
        self, source: SourceIdentity, language: str, *, include_optional: bool = False
    ) -> TranscriptResolution:
        attempts: list[TranscriptAttempt] = []
        metadata_title: str | None = None
        metadata_chapters: tuple[Chapter, ...] = ()
        if source.kind == SourceKind.LOCAL_MEDIA:
            providers = self.local_providers
        else:
            providers = (*self.providers, *self.optional_providers) if include_optional else self.providers
        deadline = time.monotonic() + self.acquisition_timeout_seconds
        for provider in providers:
            candidate, reasons = await self._fetch_with_deadline(provider, source, language, deadline)
            if "acquisition_timeout" in reasons:
                attempts.append(TranscriptAttempt(provider.name, reasons))
                break
            for retry in range(self.rate_limit_retries):
                if candidate is not None or "rate_limited" not in reasons:
                    break
                delay = self.retry_delay_seconds * (2**retry)
                if time.monotonic() + delay >= deadline:
                    reasons = ("acquisition_timeout",)
                    break
                await asyncio.sleep(delay)
                candidate, reasons = await self._fetch_with_deadline(provider, source, language, deadline)
                if "acquisition_timeout" in reasons:
                    break
            if candidate is None:
                attempt_metadata = getattr(provider, "attempt_metadata", None)
                if callable(attempt_metadata):
                    provider_title, provider_chapters = attempt_metadata()
                    metadata_title = metadata_title or provider_title
                    metadata_chapters = metadata_chapters or provider_chapters
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
        recorded_attempts = tuple(attempts)
        if recorded_attempts and all("rate_limited" in attempt.reasons for attempt in recorded_attempts):
            retry_after = max(1, round(self.retry_delay_seconds * (2**self.rate_limit_retries)))
            raise TranscriptRateLimited(recorded_attempts, retry_after)
        raise TranscriptUnavailable(recorded_attempts)

    async def _fetch_with_deadline(
        self,
        provider: TranscriptProvider,
        source: SourceIdentity,
        language: str,
        deadline: float,
    ) -> tuple[Transcript | None, tuple[str, ...]]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None, ("acquisition_timeout",)
        try:
            candidate = await asyncio.wait_for(
                provider.fetch(source, language), timeout=min(self.provider_timeout_seconds, remaining)
            )
        except TimeoutError:
            reason = "acquisition_timeout" if time.monotonic() >= deadline else "provider_timeout"
            return None, (reason,)
        attempt_reasons = getattr(provider, "attempt_reasons", None)
        reasons = attempt_reasons() if callable(attempt_reasons) else ()
        return candidate, reasons
