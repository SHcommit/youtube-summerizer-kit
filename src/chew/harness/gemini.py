"""Gemini CLI headless adapter."""

from __future__ import annotations

import json

from chew.domain import GenerationRequest, GenerationResult
from chew.harness.base import HarnessProbe
from chew.harness.builtin import (
    CliHarnessBase,
    HarnessExecutionError,
    ensure_success,
    parse_json_object,
    request_prompt,
)


class GeminiHarness(CliHarnessBase):
    runtime_id = "gemini"
    executable_name = "gemini"
    maximum_concurrency = 2

    async def probe(self) -> HarnessProbe:
        probe = await super().probe()
        if not probe.available:
            return probe
        return probe.model_copy(
            update={
                "auth_ready": None,
                "detail": "인증 상태는 첫 생성 요청에서 검증됩니다.",
            }
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        return await self._generate_prompt(request_prompt(request), request.request_id, request.timeout_ms)

    async def generate_prompt(self, prompt: str, *, request_id: str, timeout_ms: int = 120_000) -> GenerationResult:
        """Run a raw headless prompt for the direct-video benchmark baseline."""

        return await self._generate_prompt(prompt, request_id, timeout_ms)

    async def _generate_prompt(self, prompt: str, request_id: str, timeout_ms: int) -> GenerationResult:
        if self.executable is None:
            raise HarnessExecutionError("gemini 실행 파일을 찾지 못했습니다")
        result = await self.executor.run(
            (
                self.executable,
                "--prompt",
                "Read stdin and return the requested JSON object.",
                "--output-format",
                "json",
            ),
            prompt,
            timeout_ms / 1_000,
        )
        ensure_success(self.runtime_id, result)
        envelope = json.loads(result.stdout)
        response = envelope.get("response")
        if not isinstance(response, str):
            raise HarnessExecutionError("Gemini 응답을 찾지 못했습니다")
        raw_stats = envelope.get("stats", {})
        usage = {
            key: int(value)
            for key, value in raw_stats.items()
            if isinstance(value, int) and not isinstance(value, bool)
        }
        return GenerationResult(
            request_id=request_id,
            output=parse_json_object(response),
            runtime_id=self.runtime_id,
            usage=usage,
        )
