from __future__ import annotations

from chew.harness.base import ConfigurableHarness


class FakeConfigurableHarness:
    runtime_id = "fake"

    def set_preference(self, runtime_id: str) -> None:
        self.preference = runtime_id

    async def generate(self, request: object) -> object:
        raise NotImplementedError

    async def probe(self) -> object:
        raise NotImplementedError


class FakePlainHarness:
    runtime_id = "plain"

    async def generate(self, request: object) -> object:
        raise NotImplementedError

    async def probe(self) -> object:
        raise NotImplementedError


def test_configurable_harness_isinstance_matches_set_preference() -> None:
    assert isinstance(FakeConfigurableHarness(), ConfigurableHarness)


def test_plain_harness_is_not_configurable() -> None:
    assert not isinstance(FakePlainHarness(), ConfigurableHarness)
