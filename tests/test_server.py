"""Tests for the FastAPI health/readiness server (§7-5).

Skipped automatically when fastapi is not installed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from chew.server import create_app  # noqa: E402


def test_health_returns_200_and_ok_status() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_without_database_returns_200_when_no_db_configured() -> None:
    """When no database is injected, readiness skips the DB check."""
    client = TestClient(create_app())
    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "not configured"


def test_readiness_with_working_database_returns_ready(tmp_path: Path) -> None:
    from chew.storage.database import Database

    db = Database(tmp_path / "state.db")
    db.initialize()
    client = TestClient(create_app(database=db))
    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"


def test_readiness_with_broken_database_returns_503(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from chew.storage.database import Database

    db = Database(tmp_path / "state.db")
    db.initialize()

    def _broken_active_job_count(run_id: str) -> int:
        raise RuntimeError("DB connection lost")

    monkeypatch.setattr(db, "active_job_count", _broken_active_job_count)
    client = TestClient(create_app(database=db))
    response = client.get("/readiness")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "error" in data["checks"]["database"]
