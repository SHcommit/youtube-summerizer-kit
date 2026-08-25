"""Codex CLI adapter using non-interactive JSONL and output schema support."""

from __future__ import annotations

import json
import os
import tempfile
from copy import deepcopy
from typing import Any

from chew.domain import GenerationRequest, GenerationResult
from chew.harness.builtin import (
    CliHarnessBase,
    HarnessExecutionError,
    ensure_success,
    parse_json_object,
    request_prompt,
)


class CodexHarness(CliHarnessBase):
    runtime_id = "codex"
    executable_name = "codex"
    maximum_concurrency = 8

    def authentication_command(self) -> tuple[str, ...] | None:
        return None if self.executable is None else (self.executable, "login", "status")

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.executable is None:
            raise HarnessExecutionError("codex 실행 파일을 찾지 못했습니다")
        descriptor, schema_path = tempfile.mkstemp(prefix="chew-schema-", suffix=".json")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as schema:
                json.dump(_strict_output_schema(request.output_schema), schema, ensure_ascii=False)
            argv = (
                self.executable,
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--json",
                "--output-schema",
                schema_path,
                "-",
            )
            result = await self.executor.run(argv, request_prompt(request), request.timeout_ms / 1_000)
        finally:
            if os.path.exists(schema_path):
                os.unlink(schema_path)
        ensure_success(self.runtime_id, result)
        final_text: str | None = None
        usage: dict[str, int] = {}
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    final_text = item.get("text")
            if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
                usage = {key: int(value) for key, value in event["usage"].items()}
        if not isinstance(final_text, str):
            raise HarnessExecutionError("Codex 최종 메시지를 찾지 못했습니다")
        return GenerationResult(
            request_id=request.request_id,
            output=parse_json_object(final_text),
            runtime_id=self.runtime_id,
            usage=usage,
        )


def _strict_output_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize Pydantic schemas for Codex strict structured output."""

    normalized = deepcopy(schema)
    _require_all_object_properties(normalized)
    return normalized


def _require_all_object_properties(value: object) -> None:
    if isinstance(value, dict):
        value.pop("default", None)
        properties = value.get("properties")
        if isinstance(properties, dict):
            value["required"] = list(properties)
            value["additionalProperties"] = False
        elif value.get("type") == "object":
            value["additionalProperties"] = False
        if value.get("type") == "array" and isinstance(value.get("prefixItems"), list):
            value["items"] = {"type": "string"}
        for child in value.values():
            _require_all_object_properties(child)
    elif isinstance(value, list):
        for child in value:
            _require_all_object_properties(child)
