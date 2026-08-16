from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ytsum.retention import RetentionPlanner
from ytsum.storage.artifacts import ArtifactStore
from ytsum.storage.database import Database

NOW = datetime(2026, 8, 16, tzinfo=UTC)


def _age(path: Path, age: timedelta) -> None:
    timestamp = (NOW - age).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_compact_expires_temp_logs_and_only_unreachable_objects(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.sqlite3")
    database.initialize()
    store = ArtifactStore(tmp_path)
    protected = store.put_json({"protected": True})
    unreachable = store.put_json({"old": True})
    database.create_run("run", "youtube:abc", "key")
    database.set_run_pack("run", protected.digest)
    _age(store.path_for(protected), timedelta(days=10))
    _age(store.path_for(unreachable), timedelta(days=8))
    temporary = tmp_path / "temporary"
    logs = tmp_path / "logs"
    temporary.mkdir()
    logs.mkdir()
    audio = temporary / "failed.m4a"
    active = temporary / "active.part"
    log = logs / "old.log"
    audio.write_bytes(b"audio")
    active.write_bytes(b"active")
    log.write_text("log")
    _age(audio, timedelta(hours=25))
    _age(log, timedelta(days=31))

    plan = RetentionPlanner(database, store).preview(NOW, "compact")
    paths = {item.path for item in plan.items}
    assert audio in paths and log in paths and store.path_for(unreachable) in paths
    assert active not in paths
    assert store.path_for(protected) not in paths


def test_archive_preserves_all_content_addressed_objects(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.sqlite3")
    database.initialize()
    store = ArtifactStore(tmp_path)
    value = store.put_json({"old": True})
    _age(store.path_for(value), timedelta(days=100))
    plan = RetentionPlanner(database, store).preview(NOW, "archive")
    assert store.path_for(value) not in {item.path for item in plan.items}


def test_apply_removes_exact_preview_and_is_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.sqlite3")
    database.initialize()
    store = ArtifactStore(tmp_path)
    value = store.put_json({"old": True})
    _age(store.path_for(value), timedelta(days=8))
    planner = RetentionPlanner(database, store)
    plan = planner.preview(NOW, "compact")
    result = planner.apply(plan)
    assert result.removed == len(plan.items) == 1
    assert planner.apply(plan).removed == 0


def test_private_removes_intermediates_only_after_verified_export(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.sqlite3")
    database.initialize()
    store = ArtifactStore(tmp_path)
    pack = store.put_json({"pack": True})
    database.create_run("run", "youtube:abc", "key")
    database.set_run_pack("run", pack.digest)
    assert RetentionPlanner(database, store).preview(NOW, "private").items == ()
    export = tmp_path / "outside" / "index.md"
    export.parent.mkdir()
    export.write_text("verified")
    database.register_export("run", export)
    planner = RetentionPlanner(database, store)
    plan = planner.preview(NOW, "private")
    assert store.path_for(pack) in {item.path for item in plan.items}
    planner.apply(plan)
    assert export.exists()
    assert database.get_run_pack("run") is None


def test_explicit_delete_and_purge_leave_exports_outside_store(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.sqlite3")
    database.initialize()
    store = ArtifactStore(tmp_path)
    first = store.put_json({"run": 1})
    second = store.put_json({"run": 2})
    database.create_run("run-1", "youtube:one", "key-1")
    database.create_run("run-2", "youtube:two", "key-2")
    database.set_run_pack("run-1", first.digest)
    database.set_run_pack("run-2", second.digest)
    export = tmp_path.parent / f"{tmp_path.name}-export.md"
    export.write_text("keep")
    database.register_export("run-1", export)
    planner = RetentionPlanner(database, store)
    assert planner.usage()["files"] >= 3
    deletion = planner.delete_target("youtube:one")
    planner.apply(deletion)
    assert export.exists()
    assert database.target_runs("run-1") == ()
    planner.purge()
    assert database.target_runs("run-2") == ()
    assert not list(store.objects.rglob("*.json.zst"))
    export.unlink()


def test_unknown_policy_is_rejected(tmp_path: Path) -> None:
    database = Database(tmp_path / "state.sqlite3")
    database.initialize()
    with pytest.raises(ValueError, match="보존 정책"):
        RetentionPlanner(database, ArtifactStore(tmp_path)).preview(NOW, "unknown")
