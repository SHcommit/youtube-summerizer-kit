"""Composition root for standalone local application (re-exported from app.bootstrap)."""

from chew.app.bootstrap import AutoHarness, build_application, build_retention_planner

__all__ = [
    "AutoHarness",
    "build_application",
    "build_retention_planner",
]
