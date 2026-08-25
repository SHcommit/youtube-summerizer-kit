"""Presentation of the application facade's completed command result."""

from __future__ import annotations

from dataclasses import asdict

from chew.app.service import CommandResult


def command_result_data(result: CommandResult) -> dict[str, object]:
    """Return the stable machine-readable fields for a completed command."""
    data: dict[str, object] = {
        "run_id": result.run_id,
        "profile": result.profile,
        "reused": result.reused,
        "files": [str(path) for path in result.files],
        "usage": result.usage,
    }
    if result.preprocessing_stats is not None:
        data["preprocessing"] = {
            **asdict(result.preprocessing_stats),
            "token_reduction_pct": result.preprocessing_stats.token_reduction_pct,
        }
    return data
