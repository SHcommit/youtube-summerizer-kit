from __future__ import annotations

from collections import deque

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
