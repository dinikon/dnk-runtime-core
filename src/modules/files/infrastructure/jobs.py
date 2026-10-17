from datetime import UTC, datetime
from uuid import UUID, uuid5
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)

from src.modules.files.infrastructure.stored_file.jobs.purge_queue import (
    ScheduledFilePurgeQueue,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator

JOB_TYPE = "files.cleanup"
TRASH_CLEANUP_JOB_TYPE = "files.trash.cleanup"


async def schedule_trash_cleanup(
    session: AsyncSession, tenant_id: UUID, stamp: datetime
) -> None:
    """Идемпотентно регистрирует проход текущего часового окна под внешним admission."""
    if stamp.utcoffset() is None:
        raise ValueError("Trash cleanup registration time must be timezone-aware.")
    window = stamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    jobs = SqlAlchemyScheduledJobRepository(session)
    queue = ScheduledFilePurgeQueue(
        ScheduleScheduledJobUseCase(
            repository=jobs, clock=UtcClock(), uuid_generator=UUID7Generator()
        ),
        jobs,
    )
    await queue.schedule_cleanup(
        tenant_id,
        uuid5(tenant_id, f"{TRASH_CLEANUP_JOB_TYPE}:{window.isoformat()}"),
        window,
    )


async def schedule_cleanup(
    session: AsyncSession, tenant_id: UUID, stamp: datetime
) -> None:
    """Записывает одну job текущего часового окна в транзакции регистрации."""
    window = stamp.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    # Регистрация уже защищена outer admission; новый tenant ещё не виден отдельной сессии.
    scheduler = ScheduleScheduledJobUseCase(
        repository=SqlAlchemyScheduledJobRepository(session),
        clock=UtcClock(),
        uuid_generator=UUID7Generator(),
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
