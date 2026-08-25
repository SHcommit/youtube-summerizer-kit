"""Agent tool port, deliberately independent of a graph framework."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from chew.agents.contracts import AgentToolRequest, AgentToolResult


@runtime_checkable
class AgentTool(Protocol):
    """One named capability an agent policy may grant."""

    name: str

    async def invoke(self, request: AgentToolRequest) -> AgentToolResult: ...
