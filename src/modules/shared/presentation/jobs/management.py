from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.application.jobs import (
    CancelScheduledJobUseCase,
    InMemoryScheduledJobDispatcher,
    ProcessDueScheduledJobsUseCase,
    RecoverStuckScheduledJobsUseCase,
    ScheduleScheduledJobUseCase,
    ScheduledJobDispatcherPort,
    ScheduledJobHandlerPort,
    ScheduledJobRetryPolicy,
)
from src.modules.shared.application.uuid import UUIdGeneratorProtocol
from src.modules.shared.domain.time import ClockPort
from src.modules.shared.infrastructure.jobs import SqlAlchemyScheduledJobRepository
from src.modules.shared.infrastructure.time import UtcClock
from src.modules.shared.infrastructure.uuid import UUID7Generator


def build_scheduled_job_repository(
    session: AsyncSession,
) -> SqlAlchemyScheduledJobRepository:
    """Builds the shared SQLAlchemy scheduled job repository."""
    return SqlAlchemyScheduledJobRepository(session)


def build_scheduled_job_dispatcher(
    handlers: Mapping[str, ScheduledJobHandlerPort] | None = None,
) -> InMemoryScheduledJobDispatcher:
    """Builds an in-process scheduled job dispatcher registry."""
    return InMemoryScheduledJobDispatcher(handlers)


def build_schedule_scheduled_job_use_case(
    *,
    session: AsyncSession,
    clock: ClockPort | None = None,
    uuid_generator: UUIdGeneratorProtocol | None = None,
) -> ScheduleScheduledJobUseCase:
    """Builds the scheduled job scheduling use case."""
    return ScheduleScheduledJobUseCase(
        repository=build_scheduled_job_repository(session),
        clock=clock or UtcClock(),
        uuid_generator=uuid_generator or UUID7Generator(),
    )


def build_process_due_scheduled_jobs_use_case(
    *,
    session: AsyncSession,
    retry_base_seconds: int,
    dispatcher: ScheduledJobDispatcherPort | None = None,
    clock: ClockPort | None = None,
    uuid_generator: UUIdGeneratorProtocol | None = None,
) -> ProcessDueScheduledJobsUseCase:
    """Builds the due scheduled jobs processing use case."""
    return ProcessDueScheduledJobsUseCase(
        repository=build_scheduled_job_repository(session),
        dispatcher=dispatcher or build_scheduled_job_dispatcher(),
        clock=clock or UtcClock(),
        uuid_generator=uuid_generator or UUID7Generator(),
        retry_policy=ScheduledJobRetryPolicy(retry_base_seconds),
    )


def build_recover_stuck_scheduled_jobs_use_case(
    *,
    session: AsyncSession,
    clock: ClockPort | None = None,
) -> RecoverStuckScheduledJobsUseCase:
    """Builds the stuck scheduled jobs recovery use case."""
    return RecoverStuckScheduledJobsUseCase(
        repository=build_scheduled_job_repository(session),
        clock=clock or UtcClock(),
    )


def build_cancel_scheduled_job_use_case(
    *,
    session: AsyncSession,
    clock: ClockPort | None = None,
) -> CancelScheduledJobUseCase:
    """Builds the scheduled job cancellation use case."""
    return CancelScheduledJobUseCase(
        repository=build_scheduled_job_repository(session),
        clock=clock or UtcClock(),
    )


__all__ = [
    "build_cancel_scheduled_job_use_case",
    "build_process_due_scheduled_jobs_use_case",
    "build_recover_stuck_scheduled_jobs_use_case",
    "build_schedule_scheduled_job_use_case",
    "build_scheduled_job_dispatcher",
    "build_scheduled_job_repository",
]
