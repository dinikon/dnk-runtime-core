from datetime import datetime
from uuid import uuid5, NAMESPACE_URL
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.domain.jobs import ScheduledJob, ScheduledJobStatus
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.currency.domain.functional_currency.value_object.id import (
    FunctionalCurrencyPeriodIdVO,
)


class ScheduledActivationAdapter:
    """Translate Currency activation dates to the public shared scheduling contract."""

    def __init__(self, jobs: ScheduledJobRepositoryProtocol):
        self.jobs = jobs

    async def schedule(
        self,
        *,
        tenant_id: EntityIdVO,
        period_id: FunctionalCurrencyPeriodIdVO,
        run_at: datetime,
        policy_version: int,
        now: datetime,
    ) -> None:
        identifier = uuid5(
            NAMESPACE_URL,
            f"currency-activation:{tenant_id}:{period_id}:{policy_version}:{run_at.isoformat()}",
        )
        job = ScheduledJob(
            identifier,
            tenant_id.uuid,
            "currency.activate_functional",
            {"period_id": str(period_id), "policy_version": policy_version},
            run_at,
            ScheduledJobStatus.SCHEDULED.value,
            0,
            None,
            None,
            now,
            now,
        )
        await self.jobs.reconcile_schedule(
            job, payload_contains={"period_id": str(period_id)}
        )


__all__ = ["ScheduledActivationAdapter"]
