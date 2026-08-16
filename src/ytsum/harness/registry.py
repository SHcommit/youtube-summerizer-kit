"""Discovery and selection of built-in harnesses."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from ytsum.harness.antigravity import AntigravityHarness
from ytsum.harness.base import Harness, HarnessProbe
from ytsum.harness.builtin import HarnessAuthenticationError
from ytsum.harness.claude import ClaudeHarness
from ytsum.harness.codex import CodexHarness
from ytsum.harness.gemini import GeminiHarness
from ytsum.harness.ollama import OllamaHarness


class HarnessRegistry:
    def __init__(self, harnesses: Sequence[Harness]) -> None:
        self.harnesses = tuple(harnesses)

    async def probe_all(self) -> list[HarnessProbe]:
        return list(await asyncio.gather(*(harness.probe() for harness in self.harnesses)))

    async def select(self, runtime_id: str) -> Harness:
        probes = await self.probe_all()
        unauthenticated: list[HarnessProbe] = []
        unverified: list[Harness] = []
        for harness, probe in zip(self.harnesses, probes, strict=True):
            matches = runtime_id == "auto" or harness.runtime_id == runtime_id
            if matches and probe.available and probe.auth_ready is True:
                return harness
            if matches and probe.available and probe.auth_ready is None:
                unverified.append(harness)
            if matches and probe.available and probe.auth_ready is False:
                unauthenticated.append(probe)
        if unverified:
            return unverified[0]
        if unauthenticated:
            blocked = unauthenticated[0]
            login = {
                "codex": "codex login",
                "gemini": "gemini",
                "claude": "claude",
                "antigravity": "agy",
            }.get(blocked.runtime_id, blocked.runtime_id)
            raise HarnessAuthenticationError(blocked.runtime_id, login)
        raise RuntimeError(f"사용 가능한 AI 실행기가 없습니다: {runtime_id}")


def default_registry() -> HarnessRegistry:
    return HarnessRegistry(
        (
            CodexHarness(),
            GeminiHarness(),
            ClaudeHarness(),
            OllamaHarness(),
            AntigravityHarness(),
        )
    )
