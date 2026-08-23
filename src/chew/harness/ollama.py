"""Local Ollama HTTP adapter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

import httpx

from chew.domain import GenerationRequest, GenerationResult
from chew.harness.base import HarnessCapabilities, HarnessProbe
from chew.harness.builtin import HarnessExecutionError, parse_json_object, request_prompt

Transport = Callable[[dict[str, object]], Awaitable[dict[str, object]]]


class OllamaHarness:
    runtime_id = "ollama"

    def __init__(
        self,
        model: str = "qwen3:8b",
        *,
        endpoint: str = "http://127.0.0.1:11434",
        allowed_endpoints: tuple[str, ...] = (),
        transport: Transport | None = None,
    ) -> None:
        self.model = model
        self.endpoint = _validated_endpoint(endpoint, allowed_endpoints)
        self._custom_transport = transport
        self._client: httpx.AsyncClient | None = None
        self._uses_default_transport = transport is None

    def _get_client(self) -> httpx.AsyncClient:
        """Return the shared AsyncClient, creating it on first call."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=180.0)
        return self._client

    async def aclose(self) -> None:
        """Close and discard the shared HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _transport(self, payload: dict[str, object]) -> dict[str, object]:
        client = self._get_client()
        response = await client.post(
            f"{self.endpoint}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    async def probe(self) -> HarnessProbe:
        try:
            if self._uses_default_transport:
                client = self._get_client()
                response = await client.get(f"{self.endpoint}/api/tags", timeout=2.0)
                response.raise_for_status()
            else:
                await self._custom_transport({"model": self.model, "prompt": "", "stream": False})  # type: ignore[misc]
            available = True
            detail = None
        except Exception as error:
            available = False
            detail = str(error)
        return HarnessProbe(
            runtime_id=self.runtime_id,
            available=available,
            auth_ready=available,
            version=None,
            capabilities=HarnessCapabilities(structured_output=True, max_concurrency=1),
            detail=detail,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        transport = self._custom_transport or self._transport
        envelope = await transport(
            {
                "model": self.model,
                "prompt": request_prompt(request),
                "format": request.output_schema,
                "stream": False,
            }
        )
        response = envelope.get("response")
        if not isinstance(response, str):
            raise HarnessExecutionError("Ollama 응답을 찾지 못했습니다")
        prompt_count = envelope.get("prompt_eval_count", 0)
        output_count = envelope.get("eval_count", 0)
        usage = {
            "input_tokens": prompt_count if isinstance(prompt_count, int) else 0,
            "output_tokens": output_count if isinstance(output_count, int) else 0,
        }
        for response_key, usage_key in (
            ("total_duration", "total_duration_ns"),
            ("load_duration", "load_duration_ns"),
            ("prompt_eval_duration", "prompt_eval_duration_ns"),
            ("eval_duration", "eval_duration_ns"),
        ):
            value = envelope.get(response_key)
            if isinstance(value, int):
                usage[usage_key] = value
        return GenerationResult(
            request_id=request.request_id,
            output=parse_json_object(response),
            runtime_id=self.runtime_id,
            model=self.model,
            usage=usage,
        )


def _validated_endpoint(endpoint: str, allowed_endpoints: tuple[str, ...]) -> str:
    normalized = endpoint.rstrip("/")
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HarnessExecutionError("Ollama endpoint must be an absolute HTTP URL")
    if normalized in {value.rstrip("/") for value in allowed_endpoints}:
        return normalized
    if parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
        raise HarnessExecutionError("Ollama endpoint must use loopback or an explicit allowlist")
    return normalized
