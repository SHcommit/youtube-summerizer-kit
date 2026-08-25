import pytest

from chew.domain import GenerationRequest, GenerationResult
from chew.harness.base import HarnessCapabilities, HarnessProbe
from chew.harness.builtin import HarnessAuthenticationError
from chew.harness.registry import HarnessRegistry


class StubHarness:
    def __init__(self, runtime_id: str, available: bool, auth_ready: bool | None = None) -> None:
        self.runtime_id = runtime_id
        self.available = available
        self.auth_ready = available if auth_ready is None else auth_ready

    async def probe(self) -> HarnessProbe:
        return HarnessProbe(
            runtime_id=self.runtime_id,
            available=self.available,
            auth_ready=self.auth_ready,
            version="1.0" if self.available else None,
            capabilities=HarnessCapabilities(max_concurrency=1),
            detail=None,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(
            request_id=request.request_id,
            output={},
            runtime_id=self.runtime_id,
        )


@pytest.mark.asyncio
async def test_registry_probes_in_registration_order_and_selects_available() -> None:
    registry = HarnessRegistry([StubHarness("missing", False), StubHarness("ready", True)])

    probes = await registry.probe_all()

    assert [probe.runtime_id for probe in probes] == ["missing", "ready"]
    assert (await registry.select("auto")).runtime_id == "ready"


@pytest.mark.asyncio
async def test_registry_rejects_unavailable_explicit_runtime() -> None:
    registry = HarnessRegistry([StubHarness("missing", False)])

    with pytest.raises(RuntimeError, match="missing"):
        await registry.select("missing")


@pytest.mark.asyncio
async def test_registry_reports_actionable_authentication_failure() -> None:
    registry = HarnessRegistry([StubHarness("codex", True, False)])

    with pytest.raises(HarnessAuthenticationError, match="codex login"):
        await registry.select("auto")


@pytest.mark.asyncio
async def test_auto_prefers_verified_login_over_unverified_runtime() -> None:
    unverified = StubHarness("gemini", True)
    unverified.auth_ready = None
    registry = HarnessRegistry([unverified, StubHarness("claude", True)])

    assert (await registry.select("auto")).runtime_id == "claude"


@pytest.mark.asyncio
async def test_frontier_selector_excludes_available_local_ollama_runtime() -> None:
    registry = HarnessRegistry([StubHarness("ollama", True), StubHarness("gemini", True)])

    assert (await registry.select("frontier")).runtime_id == "gemini"
