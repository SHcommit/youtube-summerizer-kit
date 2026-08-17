"""Claude Code print-mode adapter."""

from __future__ import annotations

import json

from chew.domain import GenerationRequest, GenerationResult
from chew.harness.builtin import (
    CliHarnessBase,
    HarnessExecutionError,
    ensure_success,
    request_prompt,
)


class ClaudeHarness(CliHarnessBase):
    runtime_id = "claude"
    executable_name = "claude"
    maximum_concurrency = 8

    def authentication_command(self) -> tuple[str, ...] | None:
        return None if self.executable is None else (self.executable, "auth", "status")

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.executable is None:
            raise HarnessExecutionError("claude 실행 파일을 찾지 못했습니다")
        result = await self.executor.run(
            (
                self.executable,
                "--print",
                "--output-format",
                "json",
                "--json-schema",
                json.dumps(request.output_schema, ensure_ascii=False, separators=(",", ":")),
                "--tools",
                "",
            ),
            request_prompt(request),
            request.timeout_ms / 1_000,
        )
        ensure_success(self.runtime_id, result)
        envelope = json.loads(result.stdout)
        output = envelope.get("structured_output")
        if not isinstance(output, dict):
            raise HarnessExecutionError("Claude 구조화 응답을 찾지 못했습니다")
        raw_usage = envelope.get("usage", {})
        usage = {
            key: int(value)
            for key, value in raw_usage.items()
            if isinstance(value, int) and not isinstance(value, bool)
        }
        return GenerationResult(
            request_id=request.request_id,
            output=output,
            runtime_id=self.runtime_id,
            usage=usage,
        )
