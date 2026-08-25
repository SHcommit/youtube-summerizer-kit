"""Immutable response values shared by inbound interfaces."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class InterfaceProblem:
    """A safe, protocol-neutral explanation of an operation failure."""

    code: str
    message: str

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("problem code must not be empty")
        if not self.message.strip():
            raise ValueError("problem message must not be empty")


@dataclass(frozen=True, slots=True)
class InterfaceResponse:
    """Exactly one successful result or safe failure for a caller."""

    ok: bool
    data: Mapping[str, object] | None = None
    problem: InterfaceProblem | None = None

    def __post_init__(self) -> None:
        if self.ok:
            if self.data is None:
                raise ValueError("successful response requires data")
            if self.problem is not None:
                raise ValueError("successful response cannot include problem")
            object.__setattr__(self, "data", MappingProxyType(dict(self.data)))
            return
        if self.data is not None:
            raise ValueError("failed response cannot include data")
        if self.problem is None:
            raise ValueError("failed response requires problem")
