"""Bounded control-plane contracts for optional future agent workflows.

This package owns no workflow runtime.  LangGraph or another runtime may later
adapt these contracts, but cannot become a dependency of the compiler.
"""

from chew.agents.contracts import AgentBudget, AgentToolRequest, AgentToolResult, ToolGrant
from chew.agents.policy import ToolAccessDenied, invoke_granted
from chew.agents.ports import AgentTool

__all__ = [
    "AgentBudget",
    "AgentTool",
    "AgentToolRequest",
    "AgentToolResult",
    "ToolAccessDenied",
    "ToolGrant",
    "invoke_granted",
]
