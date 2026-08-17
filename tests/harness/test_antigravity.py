import json
from typing import Any

import pytest

from chew.domain import GenerationRequest
from chew.harness.antigravity import AntigravityHarness
from chew.harness.builtin import HarnessExecutionError


class FakeExecutor:
    def __init__(self, stdout: str, exit_code: int = 0) -> None:
        self.stdout = stdout
        self.exit_code = exit_code

    async def run(self, argv: tuple[str, ...], stdin: str, timeout_seconds: float) -> Any:
        class Result:
            pass

        res = Result()
        res.stdout = self.stdout
        res.exit_code = self.exit_code
        return res


@pytest.mark.asyncio
async def test_antigravity_harness_parses_json_output() -> None:
    executor = FakeExecutor(
        json.dumps(
            {
                "structured_output": {"summary": "hello from agy"},
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            }
        )
    )
    harness = AntigravityHarness(executable="/usr/local/bin/agy", executor=executor)
    req = GenerationRequest(
        request_id="req1",
        task="summarize",
        input={"test": "input"},
        output_schema={"type": "object"},
        trace_id="trace1",
    )
    result = await harness.generate(req)

    assert result.runtime_id == "antigravity"
    assert result.output == {"summary": "hello from agy"}
    assert result.usage == {"prompt_tokens": 100, "completion_tokens": 50}


@pytest.mark.asyncio
async def test_antigravity_harness_raises_error_when_executable_missing() -> None:
    harness = AntigravityHarness(executable="/nonexistent/bin/agy")
    harness.executable = None
    req = GenerationRequest(
        request_id="req2",
        task="summarize",
        input={"test": "input"},
        output_schema={"type": "object"},
        trace_id="trace2",
    )
    with pytest.raises(HarnessExecutionError, match="agy"):
        await harness.generate(req)
