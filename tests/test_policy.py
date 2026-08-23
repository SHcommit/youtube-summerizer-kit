import pytest
from pydantic import ValidationError

from chew.pipeline.policy import build_execution_plan


def test_policy_keeps_frontier_as_default_route_and_records_budget() -> None:
    plan = build_execution_plan(
        frontier_runtime_id="gemini",
        requested_task_runtimes={},
        local_accelerator_requested=False,
        local_accelerator_available=None,
        max_input_tokens=3_200,
        reserved_output_tokens=600,
    )

    assert plan.runtime_for("topic_summary") == "gemini"
    assert plan.runtime_for("compose") == "gemini"
    assert plan.fallback_runtime_id == "gemini"
    assert plan.max_input_tokens == 3_200
    assert plan.reason == "frontier_only"
    assert plan.plan_fingerprint


def test_policy_rejects_local_runtime_as_final_brain() -> None:
    with pytest.raises(ValueError, match="Frontier"):
        build_execution_plan(
            frontier_runtime_id="ollama",
            requested_task_runtimes={},
            local_accelerator_requested=False,
            local_accelerator_available=None,
            max_input_tokens=None,
            reserved_output_tokens=0,
        )


def test_policy_replaces_unavailable_ollama_task_route_with_frontier_fallback() -> None:
    plan = build_execution_plan(
        frontier_runtime_id="gemini",
        requested_task_runtimes={"topic_summary": "ollama"},
        local_accelerator_requested=True,
        local_accelerator_available=False,
        max_input_tokens=None,
        reserved_output_tokens=0,
    )

    assert plan.runtime_for("topic_summary") == "gemini"
    assert plan.local_accelerator_available is False
    assert plan.reason == "local_accelerator_unavailable"


def test_policy_rejects_available_ollama_summary_route() -> None:
    plan = build_execution_plan(
        frontier_runtime_id="gemini",
        requested_task_runtimes={"topic_summary": "ollama"},
        local_accelerator_requested=True,
        local_accelerator_available=True,
        max_input_tokens=None,
        reserved_output_tokens=0,
    )

    assert plan.runtime_for("topic_summary") == "gemini"
    assert plan.reason == "local_summary_route_not_allowed"


def test_policy_replaces_unavailable_layered_ollama_route_with_frontier_fallback() -> None:
    plan = build_execution_plan(
        frontier_runtime_id="claude",
        requested_task_runtimes={"topic_summary": "layered_ollama"},
        local_accelerator_requested=True,
        local_accelerator_available=False,
        max_input_tokens=None,
        reserved_output_tokens=0,
    )

    assert plan.runtime_for("topic_summary") == "claude"


def test_execution_plan_is_immutable_after_policy_decision() -> None:
    plan = build_execution_plan(
        frontier_runtime_id="claude",
        requested_task_runtimes={},
        local_accelerator_requested=False,
        local_accelerator_available=None,
        max_input_tokens=None,
        reserved_output_tokens=0,
    )

    with pytest.raises(ValidationError):
        plan.default_runtime_id = "ollama"  # type: ignore[misc]
