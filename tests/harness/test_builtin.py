from __future__ import annotations

import json
from pathlib import Path

import pytest

from chew.core.models import TopicSummaryDraft
from chew.domain import GenerationRequest
from chew.harness.builtin import HarnessAuthenticationError, HarnessExecutionError, parse_json_object
from chew.harness.claude import ClaudeHarness
from chew.harness.codex import CodexHarness
from chew.harness.gemini import GeminiHarness
from chew.harness.ollama import OllamaHarness
from chew.harness.process import ProcessResult

REQUEST = GenerationRequest(
    request_id="req-1",
    task="summary",
    input={"text": "hello"},
    output_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
    timeout_ms=1_000,
    trace_id="trace-1",
)


def test_parse_json_object_rejects_oversized_response() -> None:
    oversized = '{"answer":"' + "x" * 1_000_001 + '"}'

    with pytest.raises(HarnessExecutionError, match="too large"):
        parse_json_object(oversized)


def test_parse_json_object_rejects_excessive_nesting() -> None:
    payload: dict[str, object] = {}
    for _ in range(65):
        payload = {"child": payload}

    with pytest.raises(HarnessExecutionError, match="too deeply nested"):
        parse_json_object(json.dumps(payload))


def test_parse_json_object_rejects_oversized_collection() -> None:
    payload = {"items": list(range(10_001))}

    with pytest.raises(HarnessExecutionError, match="collection is too large"):
        parse_json_object(json.dumps(payload))


class Executor:
    def __init__(self, result: ProcessResult) -> None:
        self.result = result
        self.calls: list[tuple[tuple[str, ...], str]] = []
        self.schema: dict[str, object] | None = None

    async def run(self, argv: tuple[str, ...], stdin: str, timeout: float, environment: object = None) -> ProcessResult:
        self.calls.append((argv, stdin))
        if "--output-schema" in argv:
            self.schema = json.loads(Path(argv[argv.index("--output-schema") + 1]).read_text())
        return self.result


@pytest.mark.asyncio
async def test_codex_extracts_final_jsonl_message_and_usage() -> None:
    stdout = "\n".join(
        (
            '{"type":"thread.started","thread_id":"t"}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"answer\\":\\"ok\\"}"}}',
            '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}',
        )
    )
    executor = Executor(ProcessResult(0, stdout, ""))
    result = await CodexHarness(executable="codex", executor=executor).generate(REQUEST)
    assert result.output == {"answer": "ok"}
    assert result.usage == {"input_tokens": 10, "output_tokens": 2}
    assert executor.schema == {
        **REQUEST.output_schema,
        "required": ["answer"],
        "additionalProperties": False,
    }
    assert "required" not in REQUEST.output_schema
    assert executor.calls[0][0][:3] == ("codex", "exec", "--ephemeral")


@pytest.mark.asyncio
async def test_codex_marks_defaulted_schema_properties_as_required() -> None:
    stdout = "\n".join(
        (
            '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"topic_id\\":\\"topic-1\\",\\"title\\":\\"Title\\",\\"summary\\":\\"Summary\\",\\"claims\\":[],\\"concepts\\":[],\\"examples\\":[]}"}}',
            '{"type":"turn.completed","usage":{}}',
        )
    )
    executor = Executor(ProcessResult(0, stdout, ""))
    request = REQUEST.model_copy(update={"output_schema": TopicSummaryDraft.model_json_schema()})

    await CodexHarness(executable="codex", executor=executor).generate(request)

    assert executor.schema is not None
    assert set(executor.schema["required"]) == {
        "topic_id",
        "title",
        "summary",
        "claims",
        "concepts",
        "examples",
    }
    assert executor.schema["additionalProperties"] is False
    claim_draft = executor.schema["$defs"]["ClaimDraft"]
    assert set(claim_draft["required"]) == {"text", "evidence_candidates", "provenance"}
    assert claim_draft["additionalProperties"] is False
    assert '"default"' not in json.dumps(executor.schema)


@pytest.mark.asyncio
async def test_gemini_extracts_response_and_stats() -> None:
    executor = Executor(ProcessResult(0, '{"response":"{\\"answer\\":\\"gemini\\"}","stats":{"tokens":3}}', ""))
    result = await GeminiHarness(executable="gemini", executor=executor).generate(REQUEST)
    assert result.output == {"answer": "gemini"}
    assert result.usage == {"tokens": 3}
    assert "--output-format" in executor.calls[0][0]


@pytest.mark.asyncio
async def test_gemini_probe_marks_authentication_as_unverified() -> None:
    executor = Executor(ProcessResult(0, "1.2.3", ""))
    probe = await GeminiHarness(executable="gemini", executor=executor).probe()

    assert probe.available
    assert probe.auth_ready is None
    assert "첫 생성" in (probe.detail or "")


@pytest.mark.asyncio
async def test_claude_uses_native_json_schema() -> None:
    executor = Executor(
        ProcessResult(
            0,
            '{"structured_output":{"answer":"claude"},"usage":{"input_tokens":4}}',
            "",
        )
    )
    result = await ClaudeHarness(executable="claude", executor=executor).generate(REQUEST)
    assert result.output == {"answer": "claude"}
    argv = executor.calls[0][0]
    assert json.loads(argv[argv.index("--json-schema") + 1]) == REQUEST.output_schema


@pytest.mark.asyncio
async def test_auth_failure_is_classified() -> None:
    executor = Executor(ProcessResult(1, "", "Not logged in. Run codex login"))
    with pytest.raises(HarnessAuthenticationError, match="codex login"):
        await CodexHarness(executable="codex", executor=executor).generate(REQUEST)


@pytest.mark.asyncio
async def test_ollama_uses_local_http_contract() -> None:
    seen: list[dict[str, object]] = []

    async def transport(payload: dict[str, object]) -> dict[str, object]:
        seen.append(payload)
        return {"response": '{"answer":"local"}', "prompt_eval_count": 4, "eval_count": 2}

    result = await OllamaHarness(model="qwen3", transport=transport).generate(REQUEST)
    assert result.output == {"answer": "local"}
    assert seen[0]["format"] == REQUEST.output_schema
    assert result.usage == {"input_tokens": 4, "output_tokens": 2}
