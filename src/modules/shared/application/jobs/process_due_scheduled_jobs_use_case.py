from __future__ import annotations

from datetime import datetime, timedelta
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable
from src.modules.tenancy.application.tenant.tenant_admission import (
    unrestricted_admission,
)

from src.modules.shared.application.jobs.process_due_scheduled_jobs_command import (
    ProcessDueScheduledJobsCommand,
)
from src.modules.shared.application.jobs.process_due_scheduled_jobs_result_dto import (
    ProcessDueScheduledJobsResultDTO,
)
from src.modules.shared.application.jobs.scheduled_job_dispatcher_port import (
    ScheduledJobDispatcherPort,
)
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.application.jobs.scheduled_job_retry_policy import (
    ScheduledJobRetryPolicy,
)
from src.modules.shared.application.uuid import UUIdGeneratorProtocol
from src.modules.shared.domain.time import ClockPort


class ProcessDueScheduledJobsUseCase:
    """Claims and processes due shared scheduled jobs."""

    def __init__(
        self,
        *,
        repository: ScheduledJobRepositoryProtocol,
        dispatcher: ScheduledJobDispatcherPort,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
        retry_policy: ScheduledJobRetryPolicy,
        admission=unrestricted_admission,
    ) -> None:
        self._admission = admission
        self._repository = repository
        self._dispatcher = dispatcher
        self._clock = clock
        self._uuid_generator = uuid_generator
        self._retry_policy = retry_policy

    async def __call__(
        self,
        command: ProcessDueScheduledJobsCommand,
    ) -> ProcessDueScheduledJobsResultDTO:
        now = self._clock.now()
        lock_token = str(self._uuid_generator.new())
        locked_until = now + timedelta(seconds=command.lock_ttl_seconds)
        jobs = await self._repository.claim_due_jobs(
            limit=command.limit,
            now=now,
            locked_until=locked_until,
            lock_token=lock_token,
        )
        done = 0
        failed = 0
        retried = 0
        for job in jobs:
            try:
                if job.tenant_id is None:
                    outcome = await self._process_one(job, lock_token, now, command)
                else:
                    async with self._admission(job.tenant_id):
                        outcome = await self._process_one(job, lock_token, now, command)
                done += outcome[0]
                failed += outcome[1]
                retried += outcome[2]
            except TenantUnavailable:
                continue

        return ProcessDueScheduledJobsResultDTO(
            scanned=len(jobs),
            processed=len(jobs),
            done=done,
            failed=failed,
            retried=retried,
        )

    async def _process_one(
        self,
        job: ScheduledJob,
        lock_token: str,
        now: datetime,
        command: ProcessDueScheduledJobsCommand,
    ) -> tuple[int, int, int]:
        try:
            await self._dispatcher.dispatch(job)
            marked = await self._repository.mark_done(
                job_id=job.id,
                lock_token=lock_token,
                completed_at=now,
            )
            return (int(marked), 0, 0)
        except Exception as exc:
            retry_at = None
            retried = 0
            if job.attempts < command.max_attempts:
                retry_at = self._retry_policy.next_retry_at(
                    now=now,
                    attempts=job.attempts,
                )
                retried = 1
            await self._repository.mark_failed(
                job_id=job.id,
                lock_token=lock_token,
                error=str(exc),
                retry_at=retry_at,
                failed_at=now,
            )
            return (0, 1, retried)


__all__ = ["ProcessDueScheduledJobsUseCase"]
