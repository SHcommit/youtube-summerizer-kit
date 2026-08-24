"""Pure Frontier-first runtime policy compilation."""

from __future__ import annotations

from chew.core.identity import fingerprint
from chew.core.models import ExecutionPlan, TaskRoute

POLICY_VERSION = "frontier-first-v1"
LOCAL_RUNTIME_IDS = frozenset({"ollama", "layered_ollama"})


def build_execution_plan(
    *,
    frontier_runtime_id: str,
    requested_task_runtimes: dict[str, str],
    local_accelerator_requested: bool,
    local_accelerator_available: bool | None,
    max_input_tokens: int | None,
    reserved_output_tokens: int,
) -> ExecutionPlan:
    """Compile explicit routing into a reproducible plan with a safe local fallback."""

    if frontier_runtime_id in LOCAL_RUNTIME_IDS:
        raise ValueError("A Frontier runtime must be selected as the final reasoning runtime")

    routes = dict(requested_task_runtimes)
    reason = "frontier_only"
    requested_local_summary = any(runtime_id in LOCAL_RUNTIME_IDS for runtime_id in routes.values())
    if requested_local_summary:
        routes = {
            task: frontier_runtime_id
            if runtime_id in LOCAL_RUNTIME_IDS
            else runtime_id
            for task, runtime_id in routes.items()
        }
        reason = (
            "local_accelerator_unavailable"
            if local_accelerator_available is False
            else "local_summary_route_not_allowed"
        )

    task_routes = tuple(
        TaskRoute(task=task, runtime_id=runtime_id)
        for task, runtime_id in sorted(routes.items())
    )
    fingerprint_payload = {
        "policy_version": POLICY_VERSION,
        "default_runtime_id": frontier_runtime_id,
        "task_routes": [route.model_dump(mode="json") for route in task_routes],
        "fallback_runtime_id": frontier_runtime_id,
        "local_accelerator_requested": local_accelerator_requested,
        "local_accelerator_available": local_accelerator_available,
        "max_input_tokens": max_input_tokens,
        "reserved_output_tokens": reserved_output_tokens,
        "max_runtime_attempts": 2,
        "max_rate_limit_attempts": 3,
        "rate_limit_budget_ms": 60_000,
        "rate_limit_backoff_cap_ms": 5_000,
        "reason": reason,
    }
    return ExecutionPlan(
        policy_version=POLICY_VERSION,
        default_runtime_id=frontier_runtime_id,
        task_routes=task_routes,
        fallback_runtime_id=frontier_runtime_id,
        local_accelerator_requested=local_accelerator_requested,
        local_accelerator_available=local_accelerator_available,
        max_input_tokens=max_input_tokens,
        reserved_output_tokens=reserved_output_tokens,
        max_runtime_attempts=2,
        max_rate_limit_attempts=3,
        rate_limit_budget_ms=60_000,
        rate_limit_backoff_cap_ms=5_000,
        reason=reason,
        plan_fingerprint=fingerprint(fingerprint_payload),
    )
