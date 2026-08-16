from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from ytsum.cli import app
from ytsum.retention import CleanupPlan, CleanupResult


@dataclass
class Planner:
    applied: bool = False

    def preview(self, now: datetime, policy: str) -> CleanupPlan:
        return CleanupPlan(policy, now, (), ())

    def apply(self, plan: CleanupPlan) -> CleanupResult:
        self.applied = True
        return CleanupResult(0, 0)

    def usage(self) -> dict[str, int]:
        return {"files": 0, "bytes": 0}

    def delete_target(self, target: str) -> CleanupPlan:
        return CleanupPlan("delete", datetime.now(UTC), (), (target,))

    def purge(self) -> CleanupResult:
        self.applied = True
        return CleanupResult(0, 0)


@pytest.fixture
def planner(monkeypatch: pytest.MonkeyPatch) -> Planner:
    value = Planner()
    monkeypatch.setattr("ytsum.cli._retention_factory", lambda: value)
    return value


def test_cleanup_is_preview_only_unless_apply_is_explicit(planner: Planner) -> None:
    preview = CliRunner().invoke(app, ["정리", "--json"])
    applied = CliRunner().invoke(app, ["cleanup", "--apply", "--json"])
    assert preview.exit_code == applied.exit_code == 0
    assert planner.applied


def test_purge_requires_literal_confirmation(planner: Planner) -> None:
    rejected = CliRunner().invoke(app, ["완전삭제"], input="아니오\n")
    accepted = CliRunner().invoke(app, ["purge"], input="purge\n")
    assert rejected.exit_code == 1
    assert accepted.exit_code == 0
