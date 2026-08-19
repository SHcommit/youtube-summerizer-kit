"""SQLite state repository with durable jobs and expiring leases."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class JobSpec:
    job_id: str
    run_id: str
    kind: str
    priority: int
    dependencies: tuple[str, ...] = ()
    runtime_id: str = "auto"
    payload_hash: str = ""


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    run_id: str
    kind: str
    priority: int
    runtime_id: str
    worker_id: str
    attempts: int
    payload_hash: str


def _timestamp(value: datetime) -> str:
    aware = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return aware.astimezone(UTC).isoformat()


class Database:
    SCHEMA_VERSION = 4
    _local: threading.local  # class-level annotation; one per Database instance via __init__

    def __init__(self, path: Path) -> None:
        self.path = path
        self._local = threading.local()
        path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection: sqlite3.Connection | None = getattr(self._local, "connection", None)
        if connection is None:
            connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            self._local.connection = connection
        return connection

    def close(self) -> None:
        """Close and discard the thread-local connection for the current thread."""
        connection: sqlite3.Connection | None = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None

    def initialize(self) -> None:
        with self._connect() as connection:
            current_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if current_version > self.SCHEMA_VERSION:
                raise RuntimeError(
                    f"database schema {current_version} is newer than supported schema {self.SCHEMA_VERSION}"
                )
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_locator TEXT NOT NULL DEFAULT '',
                    analysis_key TEXT NOT NULL,
                    request_key TEXT NOT NULL DEFAULT '',
                    recipe_json TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    knowledge_pack_hash TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_id, analysis_key)
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority INTEGER NOT NULL,
                    runtime_id TEXT NOT NULL,
                    worker_id TEXT,
                    lease_expires_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    payload_hash TEXT NOT NULL DEFAULT '',
                    result_hash TEXT
                );
                CREATE TABLE IF NOT EXISTS job_dependencies (
                    job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
                    depends_on TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
                    PRIMARY KEY(job_id, depends_on)
                );
                CREATE TABLE IF NOT EXISTS runtime_limits (
                    runtime_id TEXT PRIMARY KEY,
                    current_limit INTEGER NOT NULL,
                    ceiling INTEGER NOT NULL,
                    success_streak INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS exports (
                    run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                    path TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(run_id, path)
                );
                CREATE TABLE IF NOT EXISTS transcript_cache (
                    source_id TEXT NOT NULL,
                    language TEXT NOT NULL,
                    artifact_hash TEXT NOT NULL,
                    transcript_hash TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(source_id, language)
                );
                CREATE TABLE IF NOT EXISTS output_cache (
                    cache_key TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    artifact_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(runs)").fetchall()}
            if "request_key" not in columns:
                connection.execute("ALTER TABLE runs ADD COLUMN request_key TEXT NOT NULL DEFAULT ''")
            if "recipe_json" not in columns:
                connection.execute("ALTER TABLE runs ADD COLUMN recipe_json TEXT NOT NULL DEFAULT ''")
            if "source_locator" not in columns:
                connection.execute("ALTER TABLE runs ADD COLUMN source_locator TEXT NOT NULL DEFAULT ''")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS runs_reuse_idx ON runs(source_id, request_key, updated_at DESC)"
            )
            connection.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    def journal_mode(self) -> str:
        with self._connect() as connection:
            row = connection.execute("PRAGMA journal_mode").fetchone()
        return str(row[0])

    def checkpoint(self) -> None:
        """Flush the WAL to the main database file."""
        with self._connect() as connection:
            connection.execute("PRAGMA wal_checkpoint(FULL)")

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute("PRAGMA user_version").fetchone()
        return int(row[0])

    def create_run(
        self,
        run_id: str,
        source_id: str,
        analysis_key: str,
        request_key: str = "",
        recipe_json: str = "",
        source_locator: str = "",
    ) -> None:
        now = _timestamp(datetime.now(UTC))
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runs(run_id, source_id, source_locator, analysis_key, request_key, "
                "recipe_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    source_id,
                    source_locator,
                    analysis_key,
                    request_key,
                    recipe_json,
                    now,
                    now,
                ),
            )

    def get_run_source_locator(self, run_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT source_locator FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None or not row[0]:
            return None
        return str(row[0])

    def get_run_recipe(self, run_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT recipe_json FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None or not row[0]:
            return None
        return str(row[0])

    def find_reusable_run(self, source_id: str, request_key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT run_id FROM runs WHERE source_id = ? AND request_key = ? "
                "AND status = 'completed' AND knowledge_pack_hash IS NOT NULL "
                "ORDER BY updated_at DESC LIMIT 1",
                (source_id, request_key),
            ).fetchone()
        return None if row is None else str(row[0])

    def cache_transcript(
        self,
        source_id: str,
        language: str,
        artifact_hash: str,
        transcript_hash: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO transcript_cache(source_id, language, artifact_hash, "
                "transcript_hash, updated_at) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(source_id, language) DO UPDATE SET "
                "artifact_hash = excluded.artifact_hash, "
                "transcript_hash = excluded.transcript_hash, "
                "updated_at = excluded.updated_at",
                (
                    source_id,
                    language,
                    artifact_hash,
                    transcript_hash,
                    _timestamp(datetime.now(UTC)),
                ),
            )

    def get_cached_transcript(self, source_id: str, language: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT artifact_hash FROM transcript_cache WHERE source_id = ? AND language = ?",
                (source_id, language),
            ).fetchone()
        return None if row is None else str(row[0])

    def cache_output(self, cache_key: str, source_id: str, artifact_hash: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO output_cache(cache_key, source_id, artifact_hash, "
                "created_at) VALUES (?, ?, ?, ?)",
                (cache_key, source_id, artifact_hash, _timestamp(datetime.now(UTC))),
            )

    def get_cached_output(self, cache_key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT artifact_hash FROM output_cache WHERE cache_key = ?", (cache_key,)
            ).fetchone()
        return None if row is None else str(row[0])

    def find_compatible_run(self, source_id: str, analysis_key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT run_id FROM runs WHERE source_id = ? AND analysis_key = ? ORDER BY updated_at DESC LIMIT 1",
                (source_id, analysis_key),
            ).fetchone()
        return None if row is None else str(row["run_id"])

    def list_run_statuses(self, run_id: str | None = None) -> list[tuple[str, str, str, int, int]]:
        query = """
            SELECT r.run_id, r.source_id, r.status,
                   SUM(CASE WHEN j.status = 'completed' THEN 1 ELSE 0 END) completed,
                   COUNT(j.job_id) total
            FROM runs r LEFT JOIN jobs j ON j.run_id = r.run_id
        """
        parameters: tuple[str, ...] = ()
        if run_id is not None:
            query += " WHERE r.run_id = ?"
            parameters = (run_id,)
        query += " GROUP BY r.run_id ORDER BY r.updated_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [(str(row[0]), str(row[1]), str(row[2]), int(row[3]), int(row[4])) for row in rows]

    def get_resumable_run(self, run_id: str | None = None) -> tuple[str, str] | None:
        query = "SELECT run_id, source_id FROM runs WHERE status != 'completed'"
        parameters: tuple[str, ...] = ()
        if run_id is not None:
            query += " AND run_id = ?"
            parameters = (run_id,)
        query += " ORDER BY updated_at DESC LIMIT 1"
        with self._connect() as connection:
            row = connection.execute(query, parameters).fetchone()
        return None if row is None else (str(row[0]), str(row[1]))

    def upsert_job(self, spec: JobSpec) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO jobs(job_id, run_id, kind, priority, runtime_id, payload_hash) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(job_id) DO NOTHING",
                (
                    spec.job_id,
                    spec.run_id,
                    spec.kind,
                    spec.priority,
                    spec.runtime_id,
                    spec.payload_hash,
                ),
            )
            connection.executemany(
                "INSERT INTO job_dependencies(job_id, depends_on) VALUES (?, ?) ON CONFLICT DO NOTHING",
                ((spec.job_id, dependency) for dependency in spec.dependencies),
            )
            connection.commit()

    def claim_ready_jobs(
        self,
        run_id: str,
        worker_id: str,
        now: datetime,
        lease_seconds: int,
        limit: int,
    ) -> list[JobRecord]:
        lease_expires = _timestamp(now + timedelta(seconds=lease_seconds))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT j.* FROM jobs j
                WHERE j.run_id = ? AND j.status = 'pending'
                  AND NOT EXISTS (
                    SELECT 1 FROM job_dependencies d
                    JOIN jobs parent ON parent.job_id = d.depends_on
                    WHERE d.job_id = j.job_id AND parent.status != 'completed'
                  )
                ORDER BY j.priority ASC, j.job_id ASC
                LIMIT ?
                """,
                (run_id, limit),
            ).fetchall()
            records: list[JobRecord] = []
            for row in rows:
                claim_id = f"{worker_id}:{uuid4()}"
                connection.execute(
                    "UPDATE jobs SET status = 'running', worker_id = ?, lease_expires_at = ?, "
                    "attempts = attempts + 1 WHERE job_id = ? AND status = 'pending'",
                    (claim_id, lease_expires, row["job_id"]),
                )
                records.append(
                    JobRecord(
                        job_id=str(row["job_id"]),
                        run_id=str(row["run_id"]),
                        kind=str(row["kind"]),
                        priority=int(row["priority"]),
                        runtime_id=str(row["runtime_id"]),
                        worker_id=claim_id,
                        attempts=int(row["attempts"]) + 1,
                        payload_hash=str(row["payload_hash"]),
                    )
                )
            connection.commit()
        return records

    def complete_job(self, job_id: str, result_hash: str, worker_id: str | None = None) -> bool:
        ownership = "" if worker_id is None else " AND worker_id = ?"
        parameters: tuple[str, ...] = (result_hash, job_id) if worker_id is None else (result_hash, job_id, worker_id)
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status = 'completed', result_hash = ?, worker_id = NULL, "
                f"lease_expires_at = NULL WHERE job_id = ?{ownership}",
                parameters,
            )
        return cursor.rowcount == 1

    def fail_job(self, job_id: str, status: str = "failed", worker_id: str | None = None) -> bool:
        ownership = "" if worker_id is None else " AND worker_id = ?"
        parameters: tuple[str, ...] = (status, job_id) if worker_id is None else (status, job_id, worker_id)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE jobs SET status = ?, worker_id = NULL, lease_expires_at = NULL WHERE job_id = ?{ownership}",
                parameters,
            )
            if cursor.rowcount == 1:
                connection.execute(
                    "UPDATE runs SET status = ?, updated_at = ? WHERE run_id = "
                    "(SELECT run_id FROM jobs WHERE job_id = ?)",
                    (status, _timestamp(datetime.now(UTC)), job_id),
                )
        return cursor.rowcount == 1

    def fail_blocked_jobs(self, run_id: str) -> int:
        total = 0
        with self._connect() as connection:
            while True:
                cursor = connection.execute(
                    """
                    UPDATE jobs SET status = 'failed'
                    WHERE run_id = ? AND status = 'pending' AND EXISTS (
                        SELECT 1 FROM job_dependencies dependency
                        JOIN jobs parent ON parent.job_id = dependency.depends_on
                        WHERE dependency.job_id = jobs.job_id
                          AND parent.status IN ('failed', 'blocked_auth')
                    )
                    """,
                    (run_id,),
                )
                if cursor.rowcount == 0:
                    break
                total += cursor.rowcount
        return total

    def retry_job(self, job_id: str, worker_id: str | None = None) -> bool:
        ownership = "" if worker_id is None else " AND worker_id = ?"
        parameters = (job_id,) if worker_id is None else (job_id, worker_id)
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status = 'pending', worker_id = NULL, lease_expires_at = NULL "
                f"WHERE job_id = ?{ownership}",
                parameters,
            )
        return cursor.rowcount == 1

    def prepare_resume(self, run_id: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status = 'pending', worker_id = NULL, lease_expires_at = NULL "
                "WHERE run_id = ? AND status IN ('failed', 'blocked_auth')",
                (run_id,),
            )
            connection.execute(
                "UPDATE runs SET status = 'pending', updated_at = ? WHERE run_id = ?",
                (_timestamp(datetime.now(UTC)), run_id),
            )
        return cursor.rowcount

    def renew_lease(self, job_id: str, worker_id: str, now: datetime, lease_seconds: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET lease_expires_at = ? WHERE job_id = ? AND worker_id = ? AND status = 'running'",
                (_timestamp(now + timedelta(seconds=lease_seconds)), job_id, worker_id),
            )
        return cursor.rowcount == 1

    def get_runtime_limit(self, runtime_id: str, ceiling: int) -> int:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runtime_limits(runtime_id, current_limit, ceiling) VALUES (?, ?, ?) "
                "ON CONFLICT(runtime_id) DO UPDATE SET ceiling = excluded.ceiling",
                (runtime_id, ceiling, ceiling),
            )
            row = connection.execute(
                "SELECT current_limit FROM runtime_limits WHERE runtime_id = ?", (runtime_id,)
            ).fetchone()
        return min(int(row[0]), ceiling)

    def note_rate_limit(self, runtime_id: str) -> int:
        with self._connect() as connection:
            connection.execute(
                "UPDATE runtime_limits SET current_limit = MAX(1, current_limit / 2), "
                "success_streak = 0 WHERE runtime_id = ?",
                (runtime_id,),
            )
            row = connection.execute(
                "SELECT current_limit FROM runtime_limits WHERE runtime_id = ?", (runtime_id,)
            ).fetchone()
        return int(row[0])

    def note_runtime_success(self, runtime_id: str) -> int:
        with self._connect() as connection:
            connection.execute(
                "UPDATE runtime_limits SET success_streak = success_streak + 1 WHERE runtime_id = ?",
                (runtime_id,),
            )
            connection.execute(
                "UPDATE runtime_limits SET current_limit = MIN(ceiling, current_limit + 1), "
                "success_streak = 0 WHERE runtime_id = ? AND success_streak >= 10",
                (runtime_id,),
            )
            row = connection.execute(
                "SELECT current_limit FROM runtime_limits WHERE runtime_id = ?", (runtime_id,)
            ).fetchone()
        return int(row[0])

    def active_job_count(self, run_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE run_id = ? AND status IN ('pending', 'running')",
                (run_id,),
            ).fetchone()
        return int(row[0])

    def completed_job_count(self, run_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE run_id = ? AND status = 'completed'",
                (run_id,),
            ).fetchone()
        return int(row[0])

    def dependency_results(self, job_id: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT parent.result_hash FROM job_dependencies dependency "
                "JOIN jobs parent ON parent.job_id = dependency.depends_on "
                "WHERE dependency.job_id = ? ORDER BY parent.job_id",
                (job_id,),
            ).fetchall()
        return [str(row[0]) for row in rows if row[0] is not None]

    def results_by_kind(self, run_id: str, kind: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT result_hash FROM jobs WHERE run_id = ? AND kind = ? AND status = 'completed' ORDER BY job_id",
                (run_id, kind),
            ).fetchall()
        return [str(row[0]) for row in rows if row[0] is not None]

    def set_run_pack(self, run_id: str, digest: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status = 'completed', knowledge_pack_hash = ?, updated_at = ? WHERE run_id = ?",
                (digest, _timestamp(datetime.now(UTC)), run_id),
            )

    def get_run_pack(self, run_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT knowledge_pack_hash FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None or row[0] is None:
            return None
        return str(row[0])

    def register_export(self, run_id: str, path: Path) -> None:
        if not path.is_file():
            raise FileNotFoundError(path)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO exports(run_id, path, verified, created_at) VALUES (?, ?, 1, ?)",
                (run_id, str(path.resolve()), _timestamp(datetime.now(UTC))),
            )

    def artifact_references(self, exclude_runs: tuple[str, ...] = ()) -> set[str]:
        clause = ""
        parameters: tuple[str, ...] = ()
        if exclude_runs:
            placeholders = ",".join("?" for _ in exclude_runs)
            clause = f" WHERE run_id NOT IN ({placeholders})"
            parameters = exclude_runs
        excluded_sources: tuple[str, ...] = ()
        with self._connect() as connection:
            if exclude_runs:
                placeholders = ",".join("?" for _ in exclude_runs)
                source_rows = connection.execute(
                    "SELECT DISTINCT source_id FROM runs candidate "
                    f"WHERE run_id IN ({placeholders}) "
                    "AND NOT EXISTS (SELECT 1 FROM runs other WHERE "
                    "other.source_id = candidate.source_id "
                    f"AND other.run_id NOT IN ({placeholders}))",
                    (*exclude_runs, *exclude_runs),
                ).fetchall()
                excluded_sources = tuple(str(row[0]) for row in source_rows)
            pack_rows = connection.execute("SELECT knowledge_pack_hash FROM runs" + clause, parameters).fetchall()
            job_rows = connection.execute("SELECT payload_hash, result_hash FROM jobs" + clause, parameters).fetchall()
            source_clause = ""
            source_parameters: tuple[str, ...] = ()
            if excluded_sources:
                source_placeholders = ",".join("?" for _ in excluded_sources)
                source_clause = f" WHERE source_id NOT IN ({source_placeholders})"
                source_parameters = excluded_sources
            transcript_rows = connection.execute(
                "SELECT artifact_hash FROM transcript_cache" + source_clause,
                source_parameters,
            ).fetchall()
            output_rows = connection.execute(
                "SELECT artifact_hash FROM output_cache" + source_clause,
                source_parameters,
            ).fetchall()
        values = {str(row[0]) for row in pack_rows if row[0]}
        values.update(str(row[0]) for row in transcript_rows if row[0])
        values.update(str(row[0]) for row in output_rows if row[0])
        for row in job_rows:
            values.update(str(value) for value in row if value)
        return values

    def private_prunable_runs(self) -> tuple[str, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT r.run_id, e.path FROM runs r JOIN exports e ON e.run_id = r.run_id "
                "WHERE r.status = 'completed' AND e.verified = 1 ORDER BY r.run_id"
            ).fetchall()
        return tuple(sorted({str(row[0]) for row in rows if Path(str(row[1])).is_file()}))

    def target_runs(self, target: str) -> tuple[str, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT run_id FROM runs WHERE run_id = ? OR source_id = ? ORDER BY run_id",
                (target, target),
            ).fetchall()
        return tuple(str(row[0]) for row in rows)

    def clear_run_artifacts(self, run_ids: tuple[str, ...], *, delete_runs: bool = False) -> None:
        if not run_ids:
            return
        placeholders = ",".join("?" for _ in run_ids)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            source_rows = connection.execute(
                f"SELECT DISTINCT source_id FROM runs candidate WHERE run_id IN ({placeholders}) "
                "AND NOT EXISTS (SELECT 1 FROM runs other WHERE "
                "other.source_id = candidate.source_id "
                f"AND other.run_id NOT IN ({placeholders}))",
                (*run_ids, *run_ids),
            ).fetchall()
            exclusive_sources = tuple(str(row[0]) for row in source_rows)
            if exclusive_sources:
                source_placeholders = ",".join("?" for _ in exclusive_sources)
                connection.execute(
                    f"DELETE FROM transcript_cache WHERE source_id IN ({source_placeholders})",
                    exclusive_sources,
                )
                connection.execute(
                    f"DELETE FROM output_cache WHERE source_id IN ({source_placeholders})",
                    exclusive_sources,
                )
            if delete_runs:
                connection.execute(f"DELETE FROM runs WHERE run_id IN ({placeholders})", run_ids)
            else:
                connection.execute(f"DELETE FROM jobs WHERE run_id IN ({placeholders})", run_ids)
                connection.execute(
                    f"UPDATE runs SET knowledge_pack_hash = NULL, status = 'discarded', "
                    f"updated_at = ? WHERE run_id IN ({placeholders})",
                    (_timestamp(datetime.now(UTC)), *run_ids),
                )
            connection.commit()

    def release_expired_leases(self, now: datetime) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status = 'pending', worker_id = NULL, lease_expires_at = NULL "
                "WHERE status = 'running' AND lease_expires_at < ?",
                (_timestamp(now),),
            )
        return cursor.rowcount
