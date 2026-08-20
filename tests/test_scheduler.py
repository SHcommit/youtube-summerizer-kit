import asyncio
import logging
from collections import Counter
from pathlib import Path
from time import monotonic

import pytest

from chew.harness.builtin import HarnessAuthenticationError
from chew.pipeline.scheduler import _backoff_sleep
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
async def test_chapter_failure_is_terminal(tmp_path: Path) -> None:
    """A chapter job that exhausts retries halts the pipeline (chapter is critical)."""
    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("topic", "run-1", "topic", 20, runtime_id="fake"))
    database.upsert_job(JobSpec("chapter", "run-1", "chapter", 10, ("topic",), "fake"))
    database.upsert_job(JobSpec("compose", "run-1", "compose", 5, ("chapter",), "fake"))

    class FailingChapterHandler(RecordingHandler):
        async def handle(self, job: JobRecord) -> str:
            if job.job_id == "chapter":
                raise ValueError("chapter synthesis failed")
            return await super().handle(job)

    handler = FailingChapterHandler({})
    with pytest.raises(ValueError, match="chapter synthesis failed"):
        await asyncio.wait_for(
            Scheduler(
                database,
                handler,
                global_concurrency=2,
                runtime_limits={"fake": 2},
            ).run("run-1"),
            timeout=2,
        )


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


@pytest.mark.asyncio
async def test_scheduler_stops_on_shutdown_event(tmp_path: Path) -> None:
    """Scheduler exits cleanly when shutdown_event is set mid-run."""
    database = database_with_run(tmp_path)
    # Add many slow jobs
    for i in range(10):
        database.upsert_job(JobSpec(f"topic-{i}", "run-1", "topic", 20, runtime_id="fake"))

    shutdown = asyncio.Event()

    class SlowHandler(RecordingHandler):
        async def handle(self, job: JobRecord) -> str:
            await asyncio.sleep(0.05)
            shutdown.set()  # signal shutdown after first job
            return f"hash-{job.job_id}"

    handler = SlowHandler({})
    scheduler = Scheduler(
        database, handler,
        global_concurrency=1,
        runtime_limits={"fake": 1},
        shutdown_event=shutdown,
    )
    summary = await scheduler.run("run-1")
    # Should have stopped early — not all 10 jobs complete
    assert summary.completed_jobs < 10


@pytest.mark.asyncio
async def test_scheduler_logs_job_completed(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("topic-log", "run-1", "topic", 20, runtime_id="fake"))
    handler = RecordingHandler({})

    with caplog.at_level(logging.INFO, logger="chew.pipeline.scheduler"):
        scheduler = Scheduler(database, handler, global_concurrency=1, runtime_limits={"fake": 1})
        await scheduler.run("run-1")

    messages = [r.getMessage() for r in caplog.records if r.name == "chew.pipeline.scheduler"]
    assert any("job_completed" in m for m in messages)


def test_backoff_sleep_increases_with_attempts() -> None:
    """Higher attempt count → higher maximum possible value returned."""
    # At attempt=0 with base=1.0, max result is 1.0.
    # At attempt=3 with base=1.0, max result is 8.0.
    # Run many trials: at least one attempt=3 result must exceed 1.0.
    results_3 = [_backoff_sleep(1.0, 3) for _ in range(100)]
    assert max(results_3) > 1.0


def test_backoff_sleep_respects_max_cap() -> None:
    """Result is always <= max_cap regardless of attempts."""
    for attempt in range(10):
        result = _backoff_sleep(1.0, attempt, max_cap=5.0)
        assert result <= 5.0


def test_backoff_sleep_is_non_negative() -> None:
    """Result is always >= 0."""
    for attempt in range(10):
        result = _backoff_sleep(1.0, attempt)
        assert result >= 0.0


def test_backoff_sleep_at_attempt_zero_bounded_by_base() -> None:
    """At attempt=0, ceiling = min(max_cap, base * 2^0) = base (if base < max_cap)."""
    # random.uniform(0, base) is always <= base
    result = _backoff_sleep(2.0, 0, max_cap=60.0)
    assert result <= 2.0


def test_backoff_sleep_saturates_at_max_cap() -> None:
    """At large attempt counts, ceiling saturates at max_cap."""
    # attempt=10: min(5.0, 1.0 * 2^10) = min(5.0, 1024) = 5.0
    result = _backoff_sleep(1.0, 10, max_cap=5.0)
    assert result <= 5.0


@pytest.mark.asyncio
async def test_scheduler_run_does_not_call_asyncio_wait(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """After the Event refactor, run() uses asyncio.wait_for+Event instead of asyncio.wait."""
    import asyncio as _asyncio

    async def _fail(*args: object, **kwargs: object) -> object:
        raise AssertionError("asyncio.wait must not be called after Event refactor")

    monkeypatch.setattr(_asyncio, "wait", _fail)

    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("topic-fast", "run-1", "topic", 20, runtime_id="fake"))
    handler = RecordingHandler({"topic-fast": 0.01})
    await Scheduler(database, handler, global_concurrency=1, runtime_limits={"fake": 1}).run("run-1")


@pytest.mark.asyncio
async def test_topic_failure_is_non_terminal_and_chapter_still_runs(tmp_path: Path) -> None:
    """A topic job that exhausts retries does not halt the pipeline — chapter proceeds."""
    database = database_with_run(tmp_path)
    database.upsert_job(JobSpec("topic-good", "run-1", "topic", 20, runtime_id="fake"))
    database.upsert_job(JobSpec("topic-bad", "run-1", "topic", 20, runtime_id="fake"))
    database.upsert_job(
        JobSpec("chapter-1", "run-1", "chapter", 10, ("topic-good", "topic-bad"), "fake")
    )

    class PartialHandler(RecordingHandler):
        async def handle(self, job: JobRecord) -> str:
            if job.job_id == "topic-bad":
                raise ValueError("permanent topic failure")
            return await super().handle(job)

    handler = PartialHandler({})
    # Must NOT raise — topic failure is non-terminal with partial failure support
    summary = await Scheduler(
        database, handler, global_concurrency=2, runtime_limits={"fake": 2}
    ).run("run-1")
    assert summary.failed_jobs >= 1
    assert handler.calls["chapter-1"] >= 1
