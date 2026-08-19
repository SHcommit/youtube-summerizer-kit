import asyncio
from collections import Counter
from pathlib import Path
from time import monotonic

import pytest

from chew.harness.builtin import HarnessAuthenticationError
from chew.scheduler import RateLimited, Scheduler
from chew.storage.database import Database, JobRecord, JobSpec


class RecordingHandler:
    def __init__(self, delays: dict[str, float]) -> None:
        self.delays = delays
        self.events: list[tuple[str, str, float]] = []
        self.calls: Counter[str] = Counter()
        self.active = 0
        self.max_active = 0

    async def handle(self, job: JobRecord) -> str:
        self.calls[job.job_id] += 1
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        self.events.append(("start", job.job_id, monotonic()))
        await asyncio.sleep(self.delays.get(job.job_id, 0.01))
        self.events.append(("end", job.job_id, monotonic()))
        self.active -= 1
        return f"hash-{job.job_id}"


def database_with_run(tmp_path: Path) -> Database:
    database = Database(tmp_path / "state.db")
    database.initialize()
    database.create_run("run-1", "youtube:abcDEF_1234", "analysis-v1")
    return database


@pytest.mark.asyncio
async def test_independent_jobs_run_in_parallel(tmp_path: Path) -> None:
    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("topic-1", "run-1", "topic", 20, runtime_id="fake"))
    database.upsert_job(JobSpec("topic-2", "run-1", "topic", 20, runtime_id="fake"))
    handler = RecordingHandler({"topic-1": 0.12, "topic-2": 0.12})
    scheduler = Scheduler(database, handler, global_concurrency=2, runtime_limits={"fake": 2})

    started = monotonic()
    await scheduler.run("run-1")

    assert monotonic() - started < 0.21
    assert handler.max_active == 2


@pytest.mark.asyncio
async def test_ready_chapter_starts_before_unrelated_topic_finishes(tmp_path: Path) -> None:
    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("topic-fast", "run-1", "topic", 20, runtime_id="fake"))
    database.upsert_job(JobSpec("topic-slow", "run-1", "topic", 20, runtime_id="fake"))
    database.upsert_job(JobSpec("chapter-fast", "run-1", "chapter", 10, ("topic-fast",), "fake"))
    handler = RecordingHandler({"topic-fast": 0.04, "topic-slow": 0.18, "chapter-fast": 0.03})
    scheduler = Scheduler(database, handler, global_concurrency=2, runtime_limits={"fake": 2})

    await scheduler.run("run-1")

    times = {(event, job): at for event, job, at in handler.events}
    assert times[("start", "chapter-fast")] < times[("end", "topic-slow")]


@pytest.mark.asyncio
async def test_runtime_limit_is_respected_and_completed_jobs_do_not_repeat(tmp_path: Path) -> None:
    database = database_with_run(tmp_path)
    for index in range(3):
        database.upsert_job(JobSpec(f"topic-{index}", "run-1", "topic", 20, runtime_id="serial"))
    handler = RecordingHandler({})
    scheduler = Scheduler(database, handler, global_concurrency=3, runtime_limits={"serial": 1})

    await scheduler.run("run-1")
    await scheduler.run("run-1")

    assert handler.max_active == 1
    assert handler.calls == Counter({"topic-0": 1, "topic-1": 1, "topic-2": 1})


@pytest.mark.asyncio
async def test_rate_limit_retries_job_and_persists_lower_concurrency(tmp_path: Path) -> None:
    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("topic-0", "run-1", "topic", 20, runtime_id="fake"))

    class RateLimitOnceHandler(RecordingHandler):
        async def handle(self, job: JobRecord) -> str:
            self.calls[job.job_id] += 1
            if self.calls[job.job_id] == 1:
                raise RateLimited(retry_after=0)
            return f"hash-{job.job_id}"

    handler = RateLimitOnceHandler({})
    scheduler = Scheduler(database, handler, global_concurrency=2, runtime_limits={"fake": 2})

    await scheduler.run("run-1")

    assert handler.calls["topic-0"] == 2
    assert database.get_runtime_limit("fake", 2) == 1


@pytest.mark.asyncio
async def test_failed_parent_marks_downstream_failed_and_scheduler_exits(tmp_path: Path) -> None:
    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("topic", "run-1", "topic", 20, runtime_id="fake"))
    database.upsert_job(JobSpec("chapter", "run-1", "chapter", 10, ("topic",), "fake"))
    database.upsert_job(JobSpec("compose", "run-1", "compose", 5, ("chapter",), "fake"))

    class FailingHandler(RecordingHandler):
        async def handle(self, job: JobRecord) -> str:
            if job.job_id == "topic":
                raise ValueError("invalid structured output")
            return await super().handle(job)

    handler = FailingHandler({})
    with pytest.raises(ValueError, match="invalid structured output"):
        await asyncio.wait_for(
            Scheduler(
                database,
                handler,
                global_concurrency=2,
                runtime_limits={"fake": 2},
            ).run("run-1"),
            timeout=1,
        )

    assert handler.calls == Counter()


@pytest.mark.asyncio
async def test_auth_block_is_actionable_and_explicit_resume_retries(tmp_path: Path) -> None:
    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("topic", "run-1", "topic", 20, runtime_id="codex"))

    class AuthOnceHandler(RecordingHandler):
        async def handle(self, job: JobRecord) -> str:
            self.calls[job.job_id] += 1
            if self.calls[job.job_id] == 1:
                raise HarnessAuthenticationError("codex", "codex login")
            return "hash"

    handler = AuthOnceHandler({})
    with pytest.raises(HarnessAuthenticationError, match="codex login"):
        await Scheduler(database, handler, global_concurrency=1, runtime_limits={"codex": 1}).run("run-1")
    assert database.list_run_statuses("run-1")[0][2] == "blocked_auth"
    database.prepare_resume("run-1")
    summary = await Scheduler(database, handler, global_concurrency=1, runtime_limits={"codex": 1}).run("run-1")
    assert summary.completed_jobs == 1
    assert handler.calls["topic"] == 2


@pytest.mark.asyncio
async def test_auth_failure_stops_new_work_and_releases_cancelled_claims(tmp_path: Path) -> None:
    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("auth", "run-1", "topic", 20, runtime_id="codex"))
    database.upsert_job(JobSpec("slow", "run-1", "topic", 20, runtime_id="codex"))

    class AuthHandler(RecordingHandler):
        async def handle(self, job: JobRecord) -> str:
            if job.job_id == "auth":
                raise HarnessAuthenticationError("codex", "codex login")
            await asyncio.sleep(5)
            return "should-not-complete"

    with pytest.raises(HarnessAuthenticationError):
        await asyncio.wait_for(
            Scheduler(
                database,
                AuthHandler({}),
                global_concurrency=2,
                runtime_limits={"codex": 2},
            ).run("run-1"),
            timeout=1,
        )

    assert database.active_job_count("run-1") == 1
