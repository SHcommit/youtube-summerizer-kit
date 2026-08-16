import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ytsum.storage.database import Database, JobSpec


def test_database_uses_wal_and_finds_compatible_run(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.initialize()
    database.create_run("run-1", "youtube:abcDEF_1234", "analysis-v1")

    assert database.journal_mode() == "wal"
    assert database.find_compatible_run("youtube:abcDEF_1234", "analysis-v1") == "run-1"
    assert database.find_compatible_run("youtube:abcDEF_1234", "analysis-v2") is None


def test_jobs_become_ready_only_after_dependencies_complete(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.initialize()
    database.create_run("run-1", "youtube:abcDEF_1234", "analysis-v1")
    database.upsert_job(JobSpec("topic-1", "run-1", "topic", 20))
    database.upsert_job(JobSpec("chapter-1", "run-1", "chapter", 10, ("topic-1",)))
    now = datetime(2026, 8, 16, tzinfo=UTC)

    first = database.claim_ready_jobs("run-1", "worker-a", now, 30, 10)
    assert [job.job_id for job in first] == ["topic-1"]

    database.complete_job("topic-1", "topic-hash")
    second = database.claim_ready_jobs("run-1", "worker-a", now, 30, 10)
    assert [job.job_id for job in second] == ["chapter-1"]


def test_expired_lease_is_claimable_by_another_worker(tmp_path: Path) -> None:
    path = tmp_path / "state.db"
    first_connection = Database(path)
    second_connection = Database(path)
    first_connection.initialize()
    first_connection.create_run("run-1", "youtube:abcDEF_1234", "analysis-v1")
    first_connection.upsert_job(JobSpec("topic-1", "run-1", "topic", 20))
    now = datetime(2026, 8, 16, tzinfo=UTC)

    first_claim = first_connection.claim_ready_jobs("run-1", "worker-a", now, 5, 1)
    assert first_claim
    assert not second_connection.claim_ready_jobs("run-1", "worker-b", now, 5, 1)

    second_connection.release_expired_leases(now + timedelta(seconds=6))
    claimed = second_connection.claim_ready_jobs(
        "run-1", "worker-b", now + timedelta(seconds=6), 5, 1
    )
    assert len(claimed) == 1
    assert claimed[0].worker_id.startswith("worker-b:")
    assert not first_connection.complete_job("topic-1", "stale", first_claim[0].worker_id)
    assert not first_connection.fail_job("topic-1", worker_id="worker-a:not-the-current-claim")
    assert not first_connection.retry_job("topic-1", worker_id="worker-a:not-the-current-claim")
    assert second_connection.complete_job("topic-1", "done", claimed[0].worker_id)


def test_initialize_migrates_pre_versioned_database(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE runs (run_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, "
            "analysis_key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
            "knowledge_pack_hash TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
            "UNIQUE(source_id, analysis_key))"
        )
    database = Database(path)
    database.initialize()
    database.create_run("new", "youtube:new", "analysis", request_key="request")
    assert database.schema_version() == Database.SCHEMA_VERSION
    assert database.find_reusable_run("youtube:new", "request") is None
    assert database.get_run_source_locator("new") is None


def test_run_preserves_source_locator_for_local_media_resume(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.db")
    database.initialize()

    database.create_run(
        "run-local",
        "local:abc",
        "analysis",
        source_locator="/recordings/meeting.mp3",
    )

    assert database.get_run_source_locator("run-local") == "/recordings/meeting.mp3"


def test_initialize_rejects_newer_database_schema(tmp_path: Path) -> None:
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as connection:
        connection.execute(f"PRAGMA user_version = {Database.SCHEMA_VERSION + 1}")
    with pytest.raises(RuntimeError, match="newer"):
        Database(path).initialize()
