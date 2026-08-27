"""Shared behavior for authenticated external CLI harnesses."""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from typing import Protocol

from chew.core.prompts import HARNESS_JSON_INSTRUCTION
from chew.domain import GenerationRequest, GenerationResult
from chew.harness.base import HarnessCapabilities, HarnessProbe, RateLimitSignal
from chew.harness.process import ProcessExecutor, ProcessResult, ProcessTimeout


class Executor(Protocol):
    async def run(
        self,
        argv: tuple[str, ...],
        stdin: str,
        timeout: float,
        environment: Mapping[str, str] | None = None,
    ) -> ProcessResult: ...


class HarnessExecutionError(RuntimeError):
    pass


class HarnessAuthenticationError(HarnessExecutionError):
    def __init__(self, runtime_id: str, login_command: str) -> None:
        self.runtime_id = runtime_id
        self.login_command = login_command
        super().__init__(f"로그인이 필요합니다. 실행: {login_command}")


class HarnessRateLimitError(HarnessExecutionError, RateLimitSignal):
    pass


MAX_JSON_RESPONSE_CHARS = 1_000_000
MAX_JSON_DEPTH = 64
MAX_JSON_COLLECTION_ITEMS = 10_000


def request_prompt(request: GenerationRequest) -> str:
    return json.dumps(
        {
            "task": request.task,
            "input": request.input,
            "output_schema": request.output_schema,
            "instruction": HARNESS_JSON_INSTRUCTION,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def parse_json_object(value: str) -> dict[str, object]:
    raw = value.strip()
    if len(raw) > MAX_JSON_RESPONSE_CHARS:
        raise HarnessExecutionError("AI response is too large")
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise HarnessExecutionError("AI 실행기가 JSON 객체를 반환하지 않았습니다.")
    _validate_json_depth(decoded)
    return decoded


def _validate_json_depth(value: object, depth: int = 1) -> None:
    if depth > MAX_JSON_DEPTH:
        raise HarnessExecutionError("AI response is too deeply nested")
    if isinstance(value, dict):
        if len(value) > MAX_JSON_COLLECTION_ITEMS:
            raise HarnessExecutionError("AI response collection is too large")
        for child in value.values():
            _validate_json_depth(child, depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_JSON_COLLECTION_ITEMS:
            raise HarnessExecutionError("AI response collection is too large")
        for child in value:
            _validate_json_depth(child, depth + 1)


def ensure_success(runtime_id: str, result: ProcessResult) -> None:
    if result.exit_code == 0:
        return
    detail = (result.stderr or result.stdout).strip()
    normalized = detail.lower()
    auth_tokens = ("not logged", "authentication", "unauthorized", "401")
    if any(token in normalized for token in auth_tokens):
        login = {"codex": "codex login", "gemini": "gemini", "claude": "claude"}.get(runtime_id, runtime_id)
        raise HarnessAuthenticationError(runtime_id, login)
    if "429" in normalized or "rate limit" in normalized or "usage limit" in normalized:
        raise HarnessRateLimitError(f"{runtime_id} 요청 한도에 도달했습니다")
    raise HarnessExecutionError(f"{runtime_id} 실행 실패({result.exit_code}): {detail}")


class CliHarnessBase:
    runtime_id = "cli"
    executable_name = ""
    maximum_concurrency = 1

    def __init__(self, *, executable: str | None = None, executor: Executor | None = None) -> None:
        self.executable = executable or shutil.which(self.executable_name)
        self.executor = executor or ProcessExecutor()

    def authentication_command(self) -> tuple[str, ...] | None:
        return None

    async def probe(self) -> HarnessProbe:
        capabilities = HarnessCapabilities(
            structured_output=True,
            streaming=False,
            max_concurrency=self.maximum_concurrency,
        )
        if self.executable is None:
            return HarnessProbe(
                runtime_id=self.runtime_id,
                available=False,
                auth_ready=False,
                version=None,
                capabilities=capabilities,
                detail=f"{self.executable_name} 실행 파일을 찾지 못했습니다",
            )
        try:
            result = await self.executor.run((self.executable, "--version"), "", 10)
        except ProcessTimeout:
            return HarnessProbe(
                runtime_id=self.runtime_id,
                available=False,
                auth_ready=False,
                version=None,
                capabilities=capabilities,
                detail=f"{self.executable_name} 실행 파일 응답 시간 초과 (10초)",
            )
        auth_ready = result.exit_code == 0
        detail = None if result.exit_code == 0 else (result.stderr or result.stdout).strip()
        auth_command = self.authentication_command()
        if result.exit_code == 0 and auth_command is not None:
            auth_result = await self.executor.run(auth_command, "", 10)
            auth_ready = auth_result.exit_code == 0
            if not auth_ready:
                detail = (auth_result.stderr or auth_result.stdout).strip()
        return HarnessProbe(
            runtime_id=self.runtime_id,
            available=result.exit_code == 0,
            auth_ready=auth_ready,
            version=(result.stdout or result.stderr).strip() or None,
            capabilities=capabilities,
            detail=detail,
        )


class UnsupportedHarness:
    def __init__(self, runtime_id: str, detail: str) -> None:
        self.runtime_id = runtime_id
        self.detail = detail

    async def probe(self) -> HarnessProbe:
        return HarnessProbe(
            runtime_id=self.runtime_id,
            available=False,
            auth_ready=False,
            version=None,
            capabilities=HarnessCapabilities(max_concurrency=1),
            detail=self.detail,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        raise HarnessExecutionError(self.detail)
