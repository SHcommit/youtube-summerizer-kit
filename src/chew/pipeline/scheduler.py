"""Dependency-aware bounded asynchronous job scheduler."""

from __future__ import annotations

import asyncio
import logging
import random
import time as _time
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from chew.core.models import ExecutionPlan
from chew.harness.base import RateLimitSignal
from chew.harness.builtin import HarnessAuthenticationError
from chew.log import job_id_var, run_id_var
from chew.storage.database import Database, JobRecord

logger = logging.getLogger(__name__)


class JobHandler(Protocol):
    async def handle(self, job: JobRecord) -> str: ...


class RateLimited(RuntimeError):
    def __init__(self, retry_after: float = 1.0) -> None:
        super().__init__("runtime rate limited")
        self.retry_after = retry_after


def _backoff_sleep(base: float, attempts: int, max_cap: float = 60.0) -> float:
    """AWS Full-Jitter exponential backoff: uniform(0, min(max_cap, base * 2^attempts))."""
    ceiling = min(max_cap, base * (2**attempts))
    return random.uniform(0, ceiling)


class AdaptiveLimiter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.active = 0
        self.condition = asyncio.Condition()

    @asynccontextmanager
    async def slot(self):  # type: ignore[no-untyped-def]
        async with self.condition:
            await self.condition.wait_for(lambda: self.active < self.limit)
            self.active += 1
        try:
            yield
        finally:
            async with self.condition:
                self.active -= 1
                self.condition.notify_all()

    async def set_limit(self, limit: int) -> None:
        async with self.condition:
            self.limit = max(1, limit)
            self.condition.notify_all()


@dataclass(frozen=True, slots=True)
class RunSummary:
    run_id: str
    completed_jobs: int
    failed_jobs: int


class Scheduler:
    def __init__(
        self,
        database: Database,
        handler: JobHandler,
        *,
        global_concurrency: int,
        runtime_limits: dict[str, int],
        lease_seconds: int = 60,
        poll_interval: float = 0.005,
        shutdown_event: asyncio.Event | None = None,
        execution_plan: ExecutionPlan | None = None,
    ) -> None:
        if global_concurrency < 1:
            raise ValueError("global_concurrency must be positive")
        self.database = database
        self.handler = handler
        self.global_concurrency = global_concurrency
        self.runtime_limiters = {
            runtime_id: AdaptiveLimiter(database.get_runtime_limit(runtime_id, limit))
            for runtime_id, limit in runtime_limits.items()
        }
        self.lease_seconds = lease_seconds
        self.poll_interval = poll_interval
        self.failed_jobs = 0
        self.terminal_error: Exception | None = None
        self.shutdown_event = shutdown_event
        self.execution_plan = execution_plan
        self._rate_limit_started_at: dict[str, float] = {}
        self._rate_limit_attempts: dict[str, int] = {}

    async def run(self, run_id: str) -> RunSummary:
        worker_id = f"worker-{uuid4()}"
        running: set[asyncio.Task[None]] = set()
        _notify = asyncio.Event()

        async def _tracked(job: JobRecord) -> None:
            try:
                await self._execute(job)
            finally:
                _notify.set()

        try:
            while (
                self.terminal_error is None
                and (self.shutdown_event is None or not self.shutdown_event.is_set())
                and self.database.active_job_count(run_id)
            ) or running:
                _notify.clear()
                finished = {task for task in running if task.done()}
                if finished:
                    await asyncio.gather(*finished)
                    running.difference_update(finished)
                    self.failed_jobs += self.database.fail_blocked_jobs(run_id)
                    if self.terminal_error is not None:
                        for task in running:
                            task.cancel()
                        if running:
                            await asyncio.gather(*running, return_exceptions=True)
                        running.clear()
                        break

                capacity = self.global_concurrency - len(running)
                shutting_down = self.shutdown_event is not None and self.shutdown_event.is_set()
                if capacity > 0 and self.terminal_error is None and not shutting_down:
                    self.database.release_expired_leases(datetime.now(UTC))
                    claimed = self.database.claim_ready_jobs(
                        run_id,
                        worker_id,
                        datetime.now(UTC),
                        self.lease_seconds,
                        capacity,
                    )
                    running.update(asyncio.create_task(_tracked(job)) for job in claimed)

                if running:
                    with suppress(TimeoutError):
                        await asyncio.wait_for(_notify.wait(), timeout=1.0)
                elif self.database.active_job_count(run_id):
                    await asyncio.sleep(self.poll_interval)
        finally:
            for task in running:
                if not task.done():
                    task.cancel()
            if running:
                await asyncio.gather(*running, return_exceptions=True)
            running.clear()

        if self.terminal_error is not None:
            raise self.terminal_error
        logger.info(
            "run_complete",
            extra={"completed_jobs": self.database.completed_job_count(run_id), "failed_jobs": self.failed_jobs},
        )
        return RunSummary(run_id, self.database.completed_job_count(run_id), self.failed_jobs)

    async def _heartbeat(self, job: JobRecord) -> None:
        interval = max(0.1, self.lease_seconds / 3)
        while True:
            await asyncio.sleep(interval)
            if not self.database.renew_lease(job.job_id, job.worker_id, datetime.now(UTC), self.lease_seconds):
                return

    async def _execute(self, job: JobRecord) -> None:
        limiter = self.runtime_limiters.setdefault(job.runtime_id, AdaptiveLimiter(1))
        rate_limit_delay: float | None = None
        async with limiter.slot():
            token_r = run_id_var.set(job.run_id)
            token_j = job_id_var.set(job.job_id)
            heartbeat = asyncio.create_task(self._heartbeat(job))
            start = _time.monotonic()
            try:
                logger.info(
                    "job_started",
                    extra={"kind": job.kind, "runtime_id": job.runtime_id, "attempts": job.attempts},
                )
                result_hash = await self.handler.handle(job)
            except (RateLimited, RateLimitSignal) as error:
                new_limit = self.database.note_rate_limit(job.runtime_id)
                await limiter.set_limit(new_limit)
                elapsed = _time.monotonic() - self._rate_limit_started_at.setdefault(
                    job.job_id, _time.monotonic()
                )
                rate_limit_attempts = self._rate_limit_attempts.get(job.job_id, 0) + 1
                self._rate_limit_attempts[job.job_id] = rate_limit_attempts
                policy = self.execution_plan
                max_attempts = policy.max_rate_limit_attempts if policy is not None else 3
                budget_seconds = (policy.rate_limit_budget_ms / 1000) if policy is not None else 60.0
                max_backoff = (
                    policy.rate_limit_backoff_cap_ms / 1000 if policy is not None else 5.0
                )
                if rate_limit_attempts >= max_attempts or elapsed >= budget_seconds:
                    self._fail_runtime(job, error, reason="rate_limit_exhausted")
                    return
                rate_limit_delay = min(
                    _backoff_sleep(error.retry_after, job.attempts, max_cap=max_backoff),
                    max(0.0, budget_seconds - elapsed),
                )
                self.database.retry_job(job.job_id, job.worker_id)
                logger.warning(
                    "rate_limited",
                    extra={
                        "runtime_id": job.runtime_id,
                        "retry_after": error.retry_after,
                        "new_limit": new_limit,
                        "attempts": rate_limit_attempts,
                        "retry_delay_seconds": rate_limit_delay,
                    },
                )
            except HarnessAuthenticationError as error:
                if self.database.fail_job(job.job_id, "blocked_auth", job.worker_id):
                    self.failed_jobs += 1
                logger.error("auth_error", extra={"runtime_id": error.runtime_id})
                self.terminal_error = error
                return
            except asyncio.CancelledError:
                self.database.retry_job(job.job_id, job.worker_id)
                logger.warning("job_cancelled", extra={"kind": job.kind})
                raise
            except Exception as error:
                err_msg = str(error).lower()
                is_quota = "usage limit" in err_msg or "quota" in err_msg
                max_attempts = (
                    self.execution_plan.max_runtime_attempts
                    if self.execution_plan is not None
                    else 2
                )
                if is_quota or job.attempts >= max_attempts:
                    self._fail_runtime(job, error, reason="runtime_exhausted")
                    return
                self.database.retry_job(job.job_id, job.worker_id)
                logger.warning(
                    "job_retried",
                    extra={"kind": job.kind, "attempts": job.attempts, "error": str(error)},
                )
                return
            finally:
                heartbeat.cancel()
                with suppress(asyncio.CancelledError):
                    await heartbeat
                run_id_var.reset(token_r)
                job_id_var.reset(token_j)
            if rate_limit_delay is None:
                latency_ms = int((_time.monotonic() - start) * 1000)
                if not self.database.complete_job(job.job_id, result_hash, job.worker_id):
                    return
                self._rate_limit_started_at.pop(job.job_id, None)
                self._rate_limit_attempts.pop(job.job_id, None)
                new_limit = self.database.note_runtime_success(job.runtime_id)
                await limiter.set_limit(new_limit)
                logger.info(
                    "job_completed",
                    extra={"kind": job.kind, "latency_ms": latency_ms, "runtime_id": job.runtime_id},
                )
                return

        if rate_limit_delay is not None:
            await asyncio.sleep(rate_limit_delay)

    def _fail_runtime(self, job: JobRecord, error: Exception, *, reason: str) -> None:
        self._rate_limit_started_at.pop(job.job_id, None)
        self._rate_limit_attempts.pop(job.job_id, None)
        if self.database.fail_job(job.job_id, "failed_runtime", job.worker_id):
            self.failed_jobs += 1
        logger.error(
            "job_failed",
            extra={"kind": job.kind, "error": str(error), "attempts": job.attempts, "reason": reason},
        )
        if job.kind != "topic":
            self.terminal_error = error
