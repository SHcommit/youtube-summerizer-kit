"""Reference-aware retention previews and safe collection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from chew.storage.artifacts import ArtifactStore
from chew.storage.database import Database

Policy = Literal["compact", "private", "archive"]


@dataclass(frozen=True, slots=True)
class CleanupItem:
    path: Path
    reason: str
    size: int


@dataclass(frozen=True, slots=True)
class CleanupPlan:
    policy: str
    created_at: datetime
    items: tuple[CleanupItem, ...]
    run_ids: tuple[str, ...]
    delete_runs: bool = False


@dataclass(frozen=True, slots=True)
class CleanupResult:
    removed: int
    bytes_freed: int


def _older_than(path: Path, now: datetime, age: timedelta) -> bool:
    modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    return modified < now - age


class RetentionPlanner:
    def __init__(self, database: Database, artifacts: ArtifactStore) -> None:
        self.database = database
        self.artifacts = artifacts

    @staticmethod
    def _item(path: Path, reason: str) -> CleanupItem:
        return CleanupItem(path, reason, path.stat().st_size)

    def preview(self, now: datetime, policy: Policy | str) -> CleanupPlan:
        items: dict[Path, CleanupItem] = {}
        run_ids: tuple[str, ...] = ()
        temporary = self.artifacts.root / "temporary"
        logs = self.artifacts.root / "logs"
        for path in temporary.rglob("*") if temporary.exists() else ():
            if path.is_file() and _older_than(path, now, timedelta(hours=24)):
                items[path] = self._item(path, "expired_temporary_media")
        for path in logs.rglob("*") if logs.exists() else ():
            if path.is_file() and _older_than(path, now, timedelta(days=30)):
                items[path] = self._item(path, "expired_log")

        if policy == "private":
            run_ids = self.database.private_prunable_runs()
            protected = self.database.artifact_references(exclude_runs=run_ids)
            candidates = self.database.artifact_references() - protected
            for digest in candidates:
                path = self.artifacts.path_for(self.artifacts.ref_for_digest(digest))
                if path.is_file():
                    items[path] = self._item(path, "private_after_export")
        elif policy == "compact":
            protected = self.database.artifact_references()
            for path in self.artifacts.objects.rglob("*.json.zst"):
                digest = path.parent.name + path.name.removesuffix(".json.zst")
                if digest not in protected and _older_than(path, now, timedelta(days=7)):
                    items[path] = self._item(path, "unreachable_object")
        elif policy != "archive":
            raise ValueError(f"알 수 없는 보존 정책: {policy}")
        ordered = tuple(sorted(items.values(), key=lambda item: str(item.path)))
        return CleanupPlan(str(policy), now, ordered, run_ids)

    def apply(self, plan: CleanupPlan) -> CleanupResult:
        self.database.clear_run_artifacts(plan.run_ids, delete_runs=plan.delete_runs)
        removed = 0
        freed = 0
        for item in plan.items:
            try:
                item.path.unlink()
            except FileNotFoundError:
                continue
            removed += 1
            freed += item.size
        return CleanupResult(removed, freed)

    def usage(self) -> dict[str, int]:
        files = [path for path in self.artifacts.root.rglob("*") if path.is_file()]
        return {"files": len(files), "bytes": sum(path.stat().st_size for path in files)}

    def delete_target(self, target: str) -> CleanupPlan:
        run_ids = self.database.target_runs(target)
        protected = self.database.artifact_references(exclude_runs=run_ids)
        candidates = self.database.artifact_references() - protected
        items = []
        for digest in candidates:
            path = self.artifacts.path_for(self.artifacts.ref_for_digest(digest))
            if path.is_file():
                items.append(self._item(path, "explicit_delete"))
        return CleanupPlan(
            "delete",
            datetime.now(UTC),
            tuple(sorted(items, key=lambda item: str(item.path))),
            run_ids,
            True,
        )

    def purge(self) -> CleanupResult:
        run_ids = tuple(row[0] for row in self.database.list_run_statuses())
        items = tuple(
            self._item(path, "explicit_purge")
            for path in self.artifacts.objects.rglob("*.json.zst")
        )
        return self.apply(CleanupPlan("purge", datetime.now(UTC), items, run_ids, True))
