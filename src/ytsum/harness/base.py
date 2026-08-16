"""Common harness capabilities and protocol."""

from __future__ import annotations

from typing import Protocol

from pydantic import Field

from ytsum.domain import FrozenModel, GenerationRequest, GenerationResult


class RateLimitSignal(RuntimeError):
    """Vendor-neutral signal used by the adaptive scheduler."""

    retry_after: float = 1.0


class HarnessCapabilities(FrozenModel):
    structured_output: bool = False
    streaming: bool = False
    image: bool = False
    video_url: bool = False
    video_file: bool = False
    max_concurrency: int = Field(default=1, ge=1)


class HarnessProbe(FrozenModel):
    runtime_id: str
    available: bool
    auth_ready: bool | None
    version: str | None
    capabilities: HarnessCapabilities
    detail: str | None


class Harness(Protocol):
    runtime_id: str

    async def probe(self) -> HarnessProbe: ...

    async def generate(self, request: GenerationRequest) -> GenerationResult: ...
