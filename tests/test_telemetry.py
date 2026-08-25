from __future__ import annotations

import asyncio
from collections import deque

import pytest

from chew.telemetry import TelemetryManager


def test_spans_is_bounded_deque() -> None:
    """TelemetryManager.spans is a deque with maxlen=10_000."""
    mgr = TelemetryManager()
    assert isinstance(mgr.spans, deque)
    assert mgr.spans.maxlen == 10_000


def test_old_spans_evicted_when_maxlen_exceeded() -> None:
    """When more than 10_000 spans are recorded, the oldest are discarded."""
    mgr = TelemetryManager()
    for i in range(10_001):
        with mgr.span(f"s{i}"):
            pass
    assert len(mgr.spans) == 10_000
    # The oldest span (s0) was evicted; the newest (s10000) is present
    names = {s.name for s in mgr.spans}
    assert "s0" not in names
    assert "s10000" in names


@pytest.mark.asyncio
async def test_run_scopes_keep_concurrent_span_collectors_isolated() -> None:
    manager = TelemetryManager()

    async def record(name: str) -> tuple[str, ...]:
        with manager.run():
            with manager.span(name):
                await asyncio.sleep(0)
            return tuple(span.name for span in manager.spans)

    first, second = await asyncio.gather(record("first"), record("second"))

    assert first == ("first",)
    assert second == ("second",)
