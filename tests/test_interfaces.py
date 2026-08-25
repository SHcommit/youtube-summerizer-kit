"""Tests for protocol-neutral operation-result presentation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from chew.app.service import CommandResult
from chew.interfaces.contracts import InterfaceProblem, InterfaceResponse
from chew.interfaces.presenters import command_result_data


def test_command_result_presenter_preserves_current_machine_shape() -> None:
    """Moving presentation out of CLI must not change integration JSON fields."""
    data = command_result_data(
        CommandResult(
            run_id="run-1",
            profile="digest",
            reused=False,
            files=(Path("out.md"),),
            usage={"input_tokens": 3},
        )
    )

    assert data == {
        "run_id": "run-1",
        "profile": "digest",
        "reused": False,
        "files": ["out.md"],
        "usage": {"input_tokens": 3},
    }


def test_success_response_is_immutable_and_copies_data() -> None:
    """A caller cannot mutate the data an interface has committed to return."""
    data = {"run_id": "run-1"}
    response = InterfaceResponse(ok=True, data=data)
    data["run_id"] = "changed"

    assert response.data == {"run_id": "run-1"}
    with pytest.raises(TypeError):
        response.data["other"] = "value"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        response.ok = False  # type: ignore[misc]


@pytest.mark.parametrize(
    ("ok", "data", "problem", "message"),
    [
        (True, None, None, "successful response requires data"),
        (
            False,
            {"run_id": "run-1"},
            InterfaceProblem(code="denied", message="Denied"),
            "failed response cannot include data",
        ),
    ],
)
def test_response_rejects_ambiguous_success_and_failure_state(
    ok: bool,
    data: dict[str, object] | None,
    problem: InterfaceProblem | None,
    message: str,
) -> None:
    """A response must be either a usable success or a usable failure."""
    with pytest.raises(ValueError, match=message):
        InterfaceResponse(ok=ok, data=data, problem=problem)
