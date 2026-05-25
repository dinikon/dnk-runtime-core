from __future__ import annotations

import asyncio
import os
import unittest
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.shared.application.jobs import (
    InMemoryScheduledJobDispatcher,
    ProcessDueScheduledJobsCommand,
    ProcessDueScheduledJobsUseCase,
    RecoverStuckJobsResultDTO,
    RecoverStuckScheduledJobsCommand,
    RecoverStuckScheduledJobsUseCase,
    ScheduleScheduledJobCommand,
    ScheduleScheduledJobUseCase,
    ScheduledJobRetryPolicy,
)
from src.modules.shared.domain.jobs import ScheduledJob, ScheduledJobStatus
from src.modules.shared.infrastructure.jobs import (
    ScheduledJobModel,
    SqlAlchemyScheduledJobRepository,
)


class _ClockStub:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _UuidStub:
    def __init__(self, *values: UUID) -> None:
        self._values = list(values)

    def new_uuid(self) -> UUID:
        return self._values.pop(0)


class _RepositoryStub:
    def __init__(self, jobs: list[ScheduledJob] | None = None) -> None:
        self.jobs = jobs or []
        self.scheduled: list[ScheduledJob] = []
        self.claim_args = None
        self.done = []
        self.failed = []
        self.canceled = []
        self.recover_result = RecoverStuckJobsResultDTO(
            scanned=0,
            recovered=0,
            failed=0,
        )

    async def schedule(self, job: ScheduledJob) -> None:
        self.scheduled.append(job)

    async def claim_due_jobs(
        self,
        *,
        limit: int,
        now: datetime,
        locked_until: datetime,
        lock_token: str,
    ) -> list[ScheduledJob]:
        self.claim_args = (limit, now, locked_until, lock_token)
        return list(self.jobs)

    async def mark_done(
        self,
        *,
        job_id: UUID,
        lock_token: str,
        completed_at: datetime,
    ) -> bool:
        self.done.append((job_id, lock_token, completed_at))
        return True

    async def mark_failed(
        self,
        *,
        job_id: UUID,
        lock_token: str,
        error: str,
        retry_at: datetime | None,
        failed_at: datetime,
    ) -> bool:
        self.failed.append((job_id, lock_token, error, retry_at, failed_at))
        return True

    async def cancel(self, *, job_id: UUID, canceled_at: datetime) -> bool:
        self.canceled.append((job_id, canceled_at))
        return True

    async def recover_stuck_jobs(
        self,
        *,
        limit: int,
        now: datetime,
        max_attempts: int,
    ) -> RecoverStuckJobsResultDTO:
        self.recover_args = (limit, now, max_attempts)
        return self.recover_result


class _HandlerStub:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.handled: list[ScheduledJob] = []

    async def handle(self, job: ScheduledJob) -> None:
        if self.fail:
            raise RuntimeError("handler failed")
        self.handled.append(job)


class _ScalarResultStub:
    def __init__(self, models: list[ScheduledJobModel]) -> None:
        self._models = models

    def all(self) -> list[ScheduledJobModel]:
        return self._models


class _ExecuteResultStub:
    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


class _SessionStub:
    def __init__(
        self,
        *,
        scalar_models: list[ScheduledJobModel] | None = None,
        rowcount: int = 1,
    ) -> None:
        self.scalar_models = scalar_models or []
        self.rowcount = rowcount
        self.added = []
        self.scalar_statement = None
        self.execute_statement = None
        self.flush_count = 0

    def add(self, model) -> None:
        self.added.append(model)

    async def scalars(self, statement):
        self.scalar_statement = statement
        return _ScalarResultStub(self.scalar_models)

    async def execute(self, statement):
        self.execute_statement = statement
        return _ExecuteResultStub(self.rowcount)

    async def flush(self) -> None:
        self.flush_count += 1


def _job(
    *,
    job_id: UUID | None = None,
    tenant_id: UUID | None = None,
    attempts: int = 1,
    status: ScheduledJobStatus = ScheduledJobStatus.RUNNING,
    now: datetime,
) -> ScheduledJob:
    return ScheduledJob(
        id=job_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        job_type="workflow.timer",
        payload={"workflow_id": "wf_1"},
        run_at=now,
        status=status.value,
        attempts=attempts,
        locked_until=now + timedelta(minutes=5),
        lock_token="lock-token",
        created_at=now,
        updated_at=now,
        last_error=None,
    )


def _model(
    *,
    job_id: UUID | None = None,
    tenant_id: UUID | None = None,
    attempts: int = 0,
    status: ScheduledJobStatus = ScheduledJobStatus.SCHEDULED,
    run_at: datetime,
    locked_until: datetime | None = None,
) -> ScheduledJobModel:
    return ScheduledJobModel(
        id=job_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        job_type="workflow.timer",
        payload={"workflow_id": "wf_1"},
        run_at=run_at,
        status=status.value,
        attempts=attempts,
        locked_until=locked_until,
        lock_token="old-token" if locked_until else None,
        created_at=run_at,
        updated_at=run_at,
        last_error=None,
    )


def _postgres_sql(statement) -> str:
    return str(statement.compile(dialect=postgresql.dialect()))


class ScheduledJobsApplicationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
        self.job_id = UUID("11111111-1111-1111-1111-111111111111")
        self.lock_id = UUID("22222222-2222-2222-2222-222222222222")
        self.tenant_id = UUID("33333333-3333-3333-3333-333333333333")

    def test_scheduled_job_serializes_round_trip_payload(self) -> None:
        job = _job(job_id=self.job_id, tenant_id=self.tenant_id, now=self.now)

        payload = job.to_payload()
        result = ScheduledJob.from_payload(payload)

        self.assertEqual(result, job)
        self.assertEqual(payload["id"], str(self.job_id))
        self.assertEqual(payload["tenant_id"], str(self.tenant_id))
        self.assertEqual(payload["run_at"], self.now.isoformat())

    async def test_schedule_future_job(self) -> None:
        repository = _RepositoryStub()
        run_at = self.now + timedelta(hours=1)
        use_case = ScheduleScheduledJobUseCase(
            repository=repository,
            clock=_ClockStub(self.now),
            uuid_generator=_UuidStub(self.job_id),
        )

        result = await use_case(
            ScheduleScheduledJobCommand(
                tenant_id=self.tenant_id,
                job_type="workflow.timer",
                payload={"workflow_id": "wf_1"},
                run_at=run_at,
            )
        )

        self.assertEqual(result.job.id, self.job_id)
        self.assertEqual(result.job.tenant_id, self.tenant_id)
        self.assertEqual(result.job.status, ScheduledJobStatus.SCHEDULED.value)
        self.assertEqual(result.job.attempts, 0)
        self.assertEqual(result.job.run_at, run_at)
        self.assertEqual(repository.scheduled, [result.job])

    async def test_successful_handler_marks_job_done(self) -> None:
        job = _job(job_id=self.job_id, tenant_id=self.tenant_id, now=self.now)
        repository = _RepositoryStub([job])
        handler = _HandlerStub()
        use_case = ProcessDueScheduledJobsUseCase(
            repository=repository,
            dispatcher=InMemoryScheduledJobDispatcher({"workflow.timer": handler}),
            clock=_ClockStub(self.now),
            uuid_generator=_UuidStub(self.lock_id),
            retry_policy=ScheduledJobRetryPolicy(30),
        )

        result = await use_case(
            ProcessDueScheduledJobsCommand(
                limit=10,
                max_attempts=5,
                lock_ttl_seconds=300,
            )
        )

        self.assertEqual(result.scanned, 1)
        self.assertEqual(result.processed, 1)
        self.assertEqual(result.done, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(handler.handled, [job])
        self.assertEqual(repository.done, [(self.job_id, str(self.lock_id), self.now)])
        self.assertEqual(
            repository.claim_args,
            (
                10,
                self.now,
                self.now + timedelta(seconds=300),
                str(self.lock_id),
            ),
        )

    async def test_failed_handler_retries_with_backoff(self) -> None:
        job = _job(job_id=self.job_id, attempts=2, now=self.now)
        repository = _RepositoryStub([job])
        use_case = ProcessDueScheduledJobsUseCase(
            repository=repository,
            dispatcher=InMemoryScheduledJobDispatcher(
                {"workflow.timer": _HandlerStub(fail=True)}
            ),
            clock=_ClockStub(self.now),
            uuid_generator=_UuidStub(self.lock_id),
            retry_policy=ScheduledJobRetryPolicy(30),
        )

        result = await use_case(ProcessDueScheduledJobsCommand(max_attempts=5))

        self.assertEqual(result.failed, 1)
        self.assertEqual(result.retried, 1)
        self.assertEqual(
            repository.failed,
            [
                (
                    self.job_id,
                    str(self.lock_id),
                    "handler failed",
                    self.now + timedelta(seconds=60),
                    self.now,
                )
            ],
        )

    async def test_exhausted_attempts_marks_failed(self) -> None:
        job = _job(job_id=self.job_id, attempts=5, now=self.now)
        repository = _RepositoryStub([job])
        use_case = ProcessDueScheduledJobsUseCase(
            repository=repository,
            dispatcher=InMemoryScheduledJobDispatcher(
                {"workflow.timer": _HandlerStub(fail=True)}
            ),
            clock=_ClockStub(self.now),
            uuid_generator=_UuidStub(self.lock_id),
            retry_policy=ScheduledJobRetryPolicy(30),
        )

        result = await use_case(ProcessDueScheduledJobsCommand(max_attempts=5))

        self.assertEqual(result.failed, 1)
        self.assertEqual(result.retried, 0)
        self.assertIsNone(repository.failed[0][3])

    async def test_missing_handler_uses_regular_retry_path(self) -> None:
        job = _job(job_id=self.job_id, attempts=1, now=self.now)
        repository = _RepositoryStub([job])
        use_case = ProcessDueScheduledJobsUseCase(
            repository=repository,
            dispatcher=InMemoryScheduledJobDispatcher(),
            clock=_ClockStub(self.now),
            uuid_generator=_UuidStub(self.lock_id),
            retry_policy=ScheduledJobRetryPolicy(30),
        )

        result = await use_case(ProcessDueScheduledJobsCommand(max_attempts=5))

        self.assertEqual(result.failed, 1)
        self.assertEqual(result.retried, 1)
        self.assertIn("No scheduled job handler registered", repository.failed[0][2])
        self.assertEqual(repository.failed[0][3], self.now + timedelta(seconds=30))

    async def test_recover_stuck_delegates_to_repository(self) -> None:
        repository = _RepositoryStub()
        repository.recover_result = RecoverStuckJobsResultDTO(
            scanned=2,
            recovered=1,
            failed=1,
        )
        use_case = RecoverStuckScheduledJobsUseCase(
            repository=repository,
            clock=_ClockStub(self.now),
        )

        result = await use_case(
            RecoverStuckScheduledJobsCommand(limit=20, max_attempts=5)
        )

        self.assertEqual(result.scanned, 2)
        self.assertEqual(repository.recover_args, (20, self.now, 5))


class ScheduledJobsRepositoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
        self.job_id = UUID("11111111-1111-1111-1111-111111111111")

    async def test_schedule_adds_scheduled_model(self) -> None:
        session = _SessionStub()
        repository = SqlAlchemyScheduledJobRepository(session)
        job = _job(job_id=self.job_id, now=self.now)

        await repository.schedule(job)

        self.assertEqual(len(session.added), 1)
        model = session.added[0]
        self.assertEqual(model.id, self.job_id)
        self.assertEqual(model.status, ScheduledJobStatus.SCHEDULED.value)
        self.assertEqual(model.attempts, 0)
        self.assertIsNone(model.locked_until)
        self.assertEqual(session.flush_count, 1)

    async def test_claim_due_filters_scheduled_due_and_sets_running_fields(
        self,
    ) -> None:
        lock_until = self.now + timedelta(minutes=5)
        model = _model(job_id=self.job_id, run_at=self.now)
        session = _SessionStub(scalar_models=[model])
        repository = SqlAlchemyScheduledJobRepository(session)

        result = await repository.claim_due_jobs(
            limit=10,
            now=self.now,
            locked_until=lock_until,
            lock_token="lock-token",
        )

        sql = _postgres_sql(session.scalar_statement)
        self.assertIn("scheduled_jobs.status =", sql)
        self.assertIn("scheduled_jobs.run_at <=", sql)
        self.assertIn("FOR UPDATE SKIP LOCKED", sql)
        self.assertEqual(result[0].id, self.job_id)
        self.assertEqual(model.status, ScheduledJobStatus.RUNNING.value)
        self.assertEqual(model.attempts, 1)
        self.assertEqual(model.locked_until, lock_until)
        self.assertEqual(model.lock_token, "lock-token")
        self.assertEqual(session.flush_count, 1)

    async def test_mark_done_requires_matching_lock_token(self) -> None:
        session = _SessionStub(rowcount=1)
        repository = SqlAlchemyScheduledJobRepository(session)

        result = await repository.mark_done(
            job_id=self.job_id,
            lock_token="lock-token",
            completed_at=self.now,
        )

        sql = _postgres_sql(session.execute_statement)
        self.assertTrue(result)
        self.assertIn("scheduled_jobs.status =", sql)
        self.assertIn("scheduled_jobs.lock_token =", sql)
        self.assertIn("UPDATE scheduled_jobs", sql)

    async def test_mark_failed_requires_matching_lock_token_and_schedules_retry(
        self,
    ) -> None:
        retry_at = self.now + timedelta(seconds=30)
        session = _SessionStub(rowcount=1)
        repository = SqlAlchemyScheduledJobRepository(session)

        result = await repository.mark_failed(
            job_id=self.job_id,
            lock_token="lock-token",
            error="boom",
            retry_at=retry_at,
            failed_at=self.now,
        )

        sql = _postgres_sql(session.execute_statement)
        self.assertTrue(result)
        self.assertIn("scheduled_jobs.lock_token =", sql)
        self.assertIn("scheduled_jobs.status =", sql)
        self.assertIn("run_at", sql)

    async def test_cancel_skips_terminal_jobs(self) -> None:
        session = _SessionStub(rowcount=1)
        repository = SqlAlchemyScheduledJobRepository(session)

        result = await repository.cancel(job_id=self.job_id, canceled_at=self.now)

        sql = _postgres_sql(session.execute_statement)
        self.assertTrue(result)
        self.assertIn("scheduled_jobs.status NOT IN", sql)
        self.assertIn("UPDATE scheduled_jobs", sql)

    async def test_recover_stuck_returns_running_jobs_to_scheduled_or_failed(
        self,
    ) -> None:
        retry_model = _model(
            job_id=self.job_id,
            attempts=2,
            status=ScheduledJobStatus.RUNNING,
            run_at=self.now - timedelta(minutes=10),
            locked_until=self.now - timedelta(seconds=1),
        )
        failed_model = _model(
            attempts=5,
            status=ScheduledJobStatus.RUNNING,
            run_at=self.now - timedelta(minutes=10),
            locked_until=self.now - timedelta(seconds=1),
        )
        session = _SessionStub(scalar_models=[retry_model, failed_model])
        repository = SqlAlchemyScheduledJobRepository(session)

        result = await repository.recover_stuck_jobs(
            limit=10,
            now=self.now,
            max_attempts=5,
        )

        sql = _postgres_sql(session.scalar_statement)
        self.assertIn("scheduled_jobs.locked_until <=", sql)
        self.assertIn("FOR UPDATE SKIP LOCKED", sql)
        self.assertEqual(result.scanned, 2)
        self.assertEqual(result.recovered, 1)
        self.assertEqual(result.failed, 1)
        self.assertEqual(retry_model.status, ScheduledJobStatus.SCHEDULED.value)
        self.assertEqual(retry_model.run_at, self.now)
        self.assertEqual(failed_model.status, ScheduledJobStatus.FAILED.value)
        self.assertIsNone(retry_model.lock_token)
        self.assertIsNone(failed_model.locked_until)


class ScheduledJobsConcurrentClaimTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_workers_do_not_claim_same_postgresql_job(self) -> None:
        database_url = os.getenv("DNK_TEST_DATABASE_URL")
        if not database_url:
            self.skipTest(
                "DNK_TEST_DATABASE_URL is not set; skipping real PostgreSQL claim test."
            )
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1,
            )
        engine = create_async_engine(database_url)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        now = datetime(2026, 5, 24, 12, 0, tzinfo=UTC)
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: ScheduledJobModel.__table__.create(
                    sync_connection,
                    checkfirst=True,
                )
            )
            await connection.execute(delete(ScheduledJobModel))

        async with session_factory() as session:
            repository = SqlAlchemyScheduledJobRepository(session)
            await repository.schedule(
                _job(now=now, status=ScheduledJobStatus.SCHEDULED)
            )
            await repository.schedule(
                _job(now=now, status=ScheduledJobStatus.SCHEDULED)
            )
            await session.commit()

        release = asyncio.Event()
        worker_ready = [asyncio.Event(), asyncio.Event()]

        async def worker(index: int) -> list[UUID]:
            async with session_factory.begin() as session:
                repository = SqlAlchemyScheduledJobRepository(session)
                jobs = await repository.claim_due_jobs(
                    limit=1,
                    now=now,
                    locked_until=now + timedelta(minutes=5),
                    lock_token=f"worker-{index}",
                )
                worker_ready[index].set()
                await asyncio.wait_for(release.wait(), timeout=5)
                return [job.id for job in jobs]

        task_1 = asyncio.create_task(worker(0))
        task_2 = asyncio.create_task(worker(1))
        await asyncio.wait_for(worker_ready[0].wait(), timeout=5)
        await asyncio.wait_for(worker_ready[1].wait(), timeout=5)
        release.set()
        result_1, result_2 = await asyncio.gather(task_1, task_2)

        self.assertTrue(set(result_1).isdisjoint(result_2))
        await engine.dispose()


__all__ = [
    "ScheduledJobsApplicationTests",
    "ScheduledJobsConcurrentClaimTests",
    "ScheduledJobsRepositoryTests",
]
