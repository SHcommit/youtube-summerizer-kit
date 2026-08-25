"""Guarded invocation for named agent-tool grants."""

from __future__ import annotations

from chew.agents.contracts import AgentToolRequest, AgentToolResult, ToolGrant
from chew.agents.ports import AgentTool


class ToolAccessDenied(PermissionError):
    """Raised before a tool invocation that is outside its declared grant."""


async def invoke_granted(
    tool: AgentTool,
    request: AgentToolRequest,
    grant: ToolGrant,
    *,
    approved: bool = False,
) -> AgentToolResult:
    """Invoke a tool only when its name, enabled state, and approval agree."""
    if tool.name != request.tool_name or grant.tool_name != request.tool_name:
        raise ToolAccessDenied("tool grant does not match request")
    if not grant.enabled:
        raise ToolAccessDenied("tool is not enabled")
    if grant.approval_required and not approved:
        raise ToolAccessDenied("tool requires explicit approval")
    return await tool.invoke(request)
