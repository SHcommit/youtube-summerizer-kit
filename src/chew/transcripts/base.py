"""Transcript provider contract."""

from typing import Protocol

from chew.domain import SourceIdentity, Transcript


def provider_failure_reason(error: Exception) -> str:
    """Map provider-specific transport failures to stable acquisition reasons."""

    status = getattr(error, "status_code", None) or getattr(error, "code", None)
    message = str(error).casefold()
    if status == 429 or "429" in message or "too many requests" in message or "rate limit" in message:
        return "rate_limited"
    if status == 403 or "403" in message or "forbidden" in message:
        return "access_denied"
    if "page needs to be reloaded" in message:
        return "session_refresh_required"
    return f"provider_error:{type(error).__name__}"


class TranscriptProvider(Protocol):
    name: str

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None: ...
