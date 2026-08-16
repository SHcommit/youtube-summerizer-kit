from __future__ import annotations

import os

import pytest

from ytsum.domain import GenerationRequest
from ytsum.harness.registry import default_registry


@pytest.mark.asyncio
async def test_opt_in_live_harnesses() -> None:
    requested = os.environ.get("YTSUM_LIVE_HARNESS")
    if not requested:
        pytest.skip("set YTSUM_LIVE_HARNESS to codex, gemini, claude, or ollama")
    harness = await default_registry().select(requested)
    result = await harness.generate(
        GenerationRequest(
            request_id="live",
            task="echo",
            input={"value": "ok"},
            output_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            trace_id="live",
        )
    )
    assert result.output["value"] == "ok"
