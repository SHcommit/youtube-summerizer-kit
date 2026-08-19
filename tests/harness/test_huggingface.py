from __future__ import annotations

import pytest

from chew.domain import GenerationRequest
from chew.harness.huggingface import HuggingFaceHarness


@pytest.mark.asyncio
async def test_huggingface_harness_generate_uses_transport() -> None:
    """generate() calls the injected transport and parses JSON output."""
    async def fake_transport(model: str, prompt: str) -> str:
        return '{"summary": "test result"}'

    harness = HuggingFaceHarness(transport=fake_transport)
    request = GenerationRequest(
        request_id="req-1",
        task="topic_summary",
        input={"topic_id": "t1", "title": "Test"},
        output_schema={"type": "object"},
        trace_id="run-1",
    )
    result = await harness.generate(request)
    assert result.output == {"summary": "test result"}
    assert result.runtime_id == "huggingface"


@pytest.mark.asyncio
async def test_huggingface_harness_probe_available_with_transport() -> None:
    """probe() returns available=True when a custom transport is injected."""
    async def fake_transport(model: str, prompt: str) -> str:
        return '{"ok": true}'

    harness = HuggingFaceHarness(transport=fake_transport)
    probe = await harness.probe()
    assert probe.available is True
    assert probe.runtime_id == "huggingface"


@pytest.mark.asyncio
async def test_huggingface_harness_probe_unavailable_without_hf_hub(monkeypatch: pytest.MonkeyPatch) -> None:
    """probe() returns available=False when huggingface_hub is not installed."""
    # Simulate missing huggingface_hub by patching the import check
    monkeypatch.setattr(
        "chew.harness.huggingface._HF_AVAILABLE", False
    )
    harness = HuggingFaceHarness()  # no transport, no HF hub
    probe = await harness.probe()
    assert probe.available is False


@pytest.mark.asyncio
async def test_huggingface_harness_generate_parses_markdown_fenced_json() -> None:
    """generate() strips markdown fences before parsing JSON."""
    async def fake_transport(model: str, prompt: str) -> str:
        return '```json\n{"key": "value"}\n```'

    harness = HuggingFaceHarness(transport=fake_transport)
    request = GenerationRequest(
        request_id="req-2",
        task="topic_summary",
        input={"topic_id": "t2", "title": "Test2"},
        output_schema={"type": "object"},
        trace_id="run-2",
    )
    result = await harness.generate(request)
    assert result.output == {"key": "value"}
