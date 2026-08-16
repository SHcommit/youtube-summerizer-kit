"""Local Ollama HTTP adapter."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import cast
from urllib.request import Request, urlopen

from ytsum.domain import GenerationRequest, GenerationResult
from ytsum.harness.base import HarnessCapabilities, HarnessProbe
from ytsum.harness.builtin import HarnessExecutionError, parse_json_object, request_prompt

Transport = Callable[[dict[str, object]], Awaitable[dict[str, object]]]


class OllamaHarness:
    runtime_id = "ollama"

    def __init__(
        self,
        model: str = "qwen3:8b",
        *,
        endpoint: str = "http://127.0.0.1:11434",
        transport: Transport | None = None,
    ) -> None:
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.transport = transport or self._transport
        self._uses_default_transport = transport is None

    async def _transport(self, payload: dict[str, object]) -> dict[str, object]:
        def send() -> dict[str, object]:
            request = Request(
                f"{self.endpoint}/api/generate",
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=180) as response:
                return cast(dict[str, object], json.loads(response.read()))

        return await asyncio.to_thread(send)

    async def probe(self) -> HarnessProbe:
        try:
            if self._uses_default_transport:

                def health() -> None:
                    with urlopen(f"{self.endpoint}/api/tags", timeout=2):
                        return

                await asyncio.to_thread(health)
            else:
                await self.transport({"model": self.model, "prompt": "", "stream": False})
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
        envelope = await self.transport(
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
        return GenerationResult(
            request_id=request.request_id,
            output=parse_json_object(response),
            runtime_id=self.runtime_id,
            model=self.model,
            usage=usage,
        )
