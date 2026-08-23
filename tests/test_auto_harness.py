import pytest

from chew.app.bootstrap import AutoHarness
from chew.core.models import GenerationRequest, GenerationResult
from chew.harness.base import HarnessCapabilities, HarnessProbe


class FakeHarness:
    def __init__(self, runtime_id: str) -> None:
        self.runtime_id = runtime_id

    async def probe(self) -> HarnessProbe:
        return HarnessProbe(
            runtime_id=self.runtime_id,
            available=True,
            auth_ready=True,
            version=None,
            capabilities=HarnessCapabilities(max_concurrency=1),
            detail=None,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(request_id=request.request_id, output={}, runtime_id=self.runtime_id)


class FakeRegistry:
    def __init__(self) -> None:
        self.harnesses = {name: FakeHarness(name) for name in ("gemini", "ollama")}

    async def select(self, runtime_id: str) -> FakeHarness:
        return self.harnesses[runtime_id]


@pytest.mark.asyncio
async def test_auto_harness_uses_explicit_task_runtime_and_default_elsewhere() -> None:
    harness = AutoHarness(FakeRegistry())  # type: ignore[arg-type]
    harness.set_preference("gemini")
    harness.set_task_preferences({"topic_summary": "ollama"})
    request = GenerationRequest(
        request_id="request",
        task="topic_summary",
        input={},
        output_schema={},
        trace_id="trace",
    )

    topic = await harness.generate(request)
    compose = await harness.generate(request.model_copy(update={"task": "compose"}))

    assert topic.runtime_id == "ollama"
    assert compose.runtime_id == "gemini"
