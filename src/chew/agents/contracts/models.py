"""Dependency-free values for bounded agent tool calls."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


def _frozen_mapping(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(values))


@dataclass(frozen=True, slots=True)
class AgentBudget:
    """Limits declared before an agent workflow starts."""

    max_steps: int
    max_model_calls: int
    deadline_seconds: int

    def __post_init__(self) -> None:
        for field_name, value in (
            ("max_steps", self.max_steps),
            ("max_model_calls", self.max_model_calls),
            ("deadline_seconds", self.deadline_seconds),
        ):
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")


@dataclass(frozen=True, slots=True)
class ToolGrant:
    """The policy decision that permits one named tool."""

    tool_name: str
    enabled: bool = True
    approval_required: bool = False

    def __post_init__(self) -> None:
        if not self.tool_name.strip():
            raise ValueError("tool_name must not be empty")


@dataclass(frozen=True, slots=True)
class AgentToolRequest:
    """Immutable input a policy has authorised for one tool call."""

    tool_name: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.tool_name.strip():
            raise ValueError("tool_name must not be empty")
        object.__setattr__(self, "payload", _frozen_mapping(self.payload))


@dataclass(frozen=True, slots=True)
class AgentToolResult:
    """Immutable, protocol-neutral result returned by an allowlisted tool."""

    tool_name: str
    data: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.tool_name.strip():
            raise ValueError("tool_name must not be empty")
        object.__setattr__(self, "data", _frozen_mapping(self.data))
