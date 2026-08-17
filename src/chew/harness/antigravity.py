"""Antigravity CLI (agy) adapter using non-interactive print mode."""

from __future__ import annotations

import json
from typing import Any

from chew.domain import GenerationRequest, GenerationResult
from chew.harness.builtin import (
    CliHarnessBase,
    HarnessExecutionError,
    ensure_success,
    parse_json_object,
    request_prompt,
)


class AntigravityHarness(CliHarnessBase):
    runtime_id = "antigravity"
    executable_name = "agy"
    maximum_concurrency = 8

    def authentication_command(self) -> tuple[str, ...] | None:
        return None

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.executable is None:
            raise HarnessExecutionError("agy (Antigravity CLI) 실행 파일을 찾지 못했습니다")
        result = await self.executor.run(
            (
                self.executable,
                "--print",
                request_prompt(request),
            ),
            "",
            request.timeout_ms / 1_000,
        )
        ensure_success(self.runtime_id, result)
        output: dict[str, Any] | None = None
        usage: dict[str, int] = {}
        try:
            envelope = json.loads(result.stdout)
            if isinstance(envelope, dict):
                output = envelope.get("structured_output") or envelope.get("output")
                if isinstance(envelope.get("usage"), dict):
                    usage = {
                        key: int(val)
                        for key, val in envelope["usage"].items()
                        if isinstance(val, (int, float)) and not isinstance(val, bool)
                    }
        except json.JSONDecodeError:
            pass

        if output is None:
            output = parse_json_object(result.stdout)

        return GenerationResult(
            request_id=request.request_id,
            output=output,
            runtime_id=self.runtime_id,
            usage=usage,
        )
