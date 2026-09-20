from sqlalchemy import select, func
from src.modules.shared.domain.jobs import ScheduledJob, ScheduledJobStatus
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.jobs.scheduled_job_model import ScheduledJobModel
from src.modules.price_lists.application.sync_run.job_identity import (
    deterministic_job_id,
    deterministic_cleanup_job_id,
)
from src.modules.price_lists.domain.sync_run.error import LostJobLease


class ScheduledJobsAdapter:
    """Адаптирует VO модуля к общему scheduled-jobs repository."""

    def __init__(self, session, clock, identifiers):
        self.session = session
        self.repository = SqlAlchemyScheduledJobRepository(session)
        self.clock = clock
        self.identifiers = identifiers

    async def schedule_sync(
        self, tenant_id, price_list_id, revision, run_at, trigger, *, job_id=None
    ):
        """Идемпотентно планирует CRON occurrence или ручной запуск."""
        job_id = job_id or deterministic_job_id(
            tenant_id, price_list_id, revision, run_at.isoformat()
        )
        now = self.clock.now()
        await self.repository.schedule_once(
            ScheduledJob(
                id=job_id.uuid,
                tenant_id=tenant_id.uuid,
                job_type="price_list.sync",
                payload=dict(
                    price_list_id=str(price_list_id),
                    schedule_revision=revision,
                    planned_at=run_at.isoformat(),
                    trigger=trigger,
                ),
                run_at=run_at,
                status=ScheduledJobStatus.SCHEDULED.value,
                attempts=0,
                locked_until=None,
                lock_token=None,
                created_at=now,
                updated_at=now,
            )
        )
        return job_id

    async def schedule_cleanup(self, tenant_id, run_at):
        """Идемпотентно планирует ежедневную очистку tenant staging."""
        now = self.clock.now()
        job_id = deterministic_cleanup_job_id(tenant_id, run_at.isoformat())
        await self.repository.schedule_once(
            ScheduledJob(
                id=job_id.uuid,
                tenant_id=tenant_id.uuid,
                job_type="price_list.cleanup",
                payload=dict(planned_at=run_at.isoformat()),
                run_at=run_at,
                status=ScheduledJobStatus.SCHEDULED.value,
                attempts=0,
                locked_until=None,
                lock_token=None,
                created_at=now,
                updated_at=now,
            )
        )

    async def cancel(self, tenant_id, price_list_id, now, *, delete=False):
        """Отзывает задачи прайса в той же UoW, что lifecycle mutation."""
        arguments = dict(
            tenant_id=tenant_id.uuid,
            job_type="price_list.sync",
            payload_contains={"price_list_id": str(price_list_id)},
        )
        if delete:
            return await self.repository.delete_matching(**arguments)
        return await self.repository.cancel_matching(**arguments, canceled_at=now)

    async def require_lease(self, tenant_id, job_id, token, *, fence=False):
        """Fencing перед commit блокирует recovery на время публикации."""
        if not token:
            raise LostJobLease("Scheduled job has no lock token.")
        statement = select(ScheduledJobModel.id).where(
            ScheduledJobModel.id == job_id.uuid,
            ScheduledJobModel.tenant_id == tenant_id.uuid,
            ScheduledJobModel.status == "running",
            ScheduledJobModel.lock_token == token,
            ScheduledJobModel.locked_until > func.clock_timestamp(),
        )
        if fence:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        if result.scalar_one_or_none() is None:
            raise LostJobLease("Scheduled job lease was lost.")


__all__ = ["ScheduledJobsAdapter"]
