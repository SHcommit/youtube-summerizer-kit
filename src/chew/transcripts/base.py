"""Transcript provider contract."""

from typing import Protocol

from chew.domain import SourceIdentity, Transcript


class TranscriptProvider(Protocol):
    name: str

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None: ...
