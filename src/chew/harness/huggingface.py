"""HuggingFace Inference API adapter (free tier via huggingface_hub)."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from chew.domain import GenerationRequest, GenerationResult
from chew.harness.base import HarnessCapabilities, HarnessProbe
from chew.harness.builtin import HarnessExecutionError, parse_json_object, request_prompt

try:
    from huggingface_hub import AsyncInferenceClient  # type: ignore[import-not-found]

    _HF_AVAILABLE = True
except ImportError:
    _HF_AVAILABLE = False

Transport = Callable[[str, str], Awaitable[str]]


class HuggingFaceHarness:
    runtime_id = "huggingface"

    def __init__(
        self,
        model: str = "Qwen/Qwen2.5-1.5B-Instruct",
        *,
        token: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        self.model = model
        self._token = token or os.environ.get("HF_TOKEN")
        self._custom_transport = transport
        self._client: object | None = None  # AsyncInferenceClient when available

    def _get_client(self) -> object:
        """Lazy-init AsyncInferenceClient."""
        if not _HF_AVAILABLE:
            raise HarnessExecutionError(
                "huggingface_hub is not installed. Run: uv sync --extra huggingface"
            )
        if self._client is None:
            self._client = AsyncInferenceClient(model=self.model, token=self._token)
        return self._client

    async def _transport(self, model: str, prompt: str) -> str:
        client = self._get_client()
        # AsyncInferenceClient.text_generation returns str
        result = await client.text_generation(  # type: ignore[attr-defined]
            prompt,
            max_new_tokens=1024,
            return_full_text=False,
        )
        if not isinstance(result, str):
            raise HarnessExecutionError("HuggingFace API returned non-string response")
        return result

    async def probe(self) -> HarnessProbe:
        if self._custom_transport is not None:
            return HarnessProbe(
                runtime_id=self.runtime_id,
                available=True,
                auth_ready=True,
                version=None,
                capabilities=HarnessCapabilities(structured_output=True, max_concurrency=1),
                detail=None,
            )
        if not _HF_AVAILABLE:
            return HarnessProbe(
                runtime_id=self.runtime_id,
                available=False,
                auth_ready=False,
                version=None,
                capabilities=HarnessCapabilities(structured_output=True, max_concurrency=1),
                detail="huggingface_hub not installed — run: uv sync --extra huggingface",
            )
        token_present = bool(self._token)
        return HarnessProbe(
            runtime_id=self.runtime_id,
            available=True,
            auth_ready=token_present or None,  # None = unverified (may work without token for free models)
            version=None,
            capabilities=HarnessCapabilities(structured_output=True, max_concurrency=1),
            detail=None if token_present else "HF_TOKEN not set — free-tier rate limits apply",
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        prompt = request_prompt(request)
        transport = self._custom_transport or self._transport
        raw = await transport(self.model, prompt)
        return GenerationResult(
            request_id=request.request_id,
            output=parse_json_object(raw),
            runtime_id=self.runtime_id,
            model=self.model,
            usage={},
        )
