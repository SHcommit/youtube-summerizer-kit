"""Tests for the bounded agent control-plane contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from chew.agents.contracts import AgentBudget, AgentToolRequest, AgentToolResult, ToolGrant
from chew.agents.policy import ToolAccessDenied, invoke_granted
from chew.agents.ports import AgentTool


def test_agent_budget_rejects_non_positive_limit() -> None:
    """A zero limit would let a caller define an unbounded or invalid agent run."""
    with pytest.raises(ValueError, match="max_steps"):
        AgentBudget(max_steps=0, max_model_calls=1, deadline_seconds=30)


def test_agent_tool_request_keeps_its_payload_immutable() -> None:
    """A policy decision must see the request that was originally authorised."""
    payload = {"tree_id": "tree-1"}
    request = AgentToolRequest(tool_name="read_tree", payload=payload)
    payload["tree_id"] = "changed-after-authorisation"

    assert request.payload == {"tree_id": "tree-1"}
    with pytest.raises(TypeError):
        request.payload["other"] = "value"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        request.tool_name = "render_tree"  # type: ignore[misc]


class CountingEchoTool:
    name = "read_tree"

    def __init__(self) -> None:
        self.calls = 0

    async def invoke(self, request: AgentToolRequest) -> AgentToolResult:
        self.calls += 1
        return AgentToolResult(tool_name=self.name, data=request.payload)


@pytest.mark.asyncio
async def test_disabled_grant_denies_before_tool_invocation() -> None:
    """Disabled grants must block the side-effecting tool call itself."""
    tool = CountingEchoTool()

    with pytest.raises(ToolAccessDenied, match="not enabled"):
        await invoke_granted(
            tool,
            AgentToolRequest(tool_name="read_tree", payload={"tree_id": "tree-1"}),
            ToolGrant(tool_name="read_tree", enabled=False),
        )

    assert tool.calls == 0


@pytest.mark.asyncio
async def test_approval_required_grant_needs_explicit_approval() -> None:
    """A future publish-like tool cannot run merely because it appears in an allowlist."""
    tool = CountingEchoTool()
    request = AgentToolRequest(tool_name="read_tree", payload={"tree_id": "tree-1"})
    grant = ToolGrant(tool_name="read_tree", approval_required=True)

    with pytest.raises(ToolAccessDenied, match="explicit approval"):
        await invoke_granted(tool, request, grant)
    assert tool.calls == 0

    result = await invoke_granted(tool, request, grant, approved=True)

    assert result.data == {"tree_id": "tree-1"}
    assert tool.calls == 1


def test_agent_tool_protocol_accepts_a_conforming_tool() -> None:
    """Adapters can expose tools without inheriting from a framework base class."""
    assert isinstance(CountingEchoTool(), AgentTool)
