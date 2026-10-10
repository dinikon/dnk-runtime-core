from datetime import UTC, datetime
from uuid import UUID, uuid5
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)
from src.modules.shared.presentation.jobs.management import (
    build_schedule_scheduled_job_use_case,
)
from src.modules.tenancy.application.tenant.tenant_admission import (
    unrestricted_admission,
)

JOB_TYPE = "files.cleanup"


async def schedule_cleanup(
    session: AsyncSession, tenant_id: UUID, stamp: datetime
) -> None:
    """Записывает одну job текущего часового окна в транзакции регистрации."""
    window = stamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    # Регистрация уже защищена outer admission; новый tenant ещё не виден отдельной сессии.
    scheduler = build_schedule_scheduled_job_use_case(
        session=session, admission=unrestricted_admission
    )
    await scheduler(
        ScheduleScheduledJobCommand(
            tenant_id=tenant_id,
            job_type=JOB_TYPE,
            payload={},
            run_at=window,
            job_id=uuid5(tenant_id, f"files.cleanup:{window.isoformat()}"),
        )
    )
