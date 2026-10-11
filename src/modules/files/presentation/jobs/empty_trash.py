import logging
from datetime import UTC, datetime
from uuid import UUID, uuid5
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.files.application.stored_file.command.empty_trash.command import (
    EmptyTrashCommand,
)
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.infrastructure.stored_file.jobs.purge_queue import (
    ScheduledFilePurgeQueue,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate

JOB_TYPE = "files.trash.empty"
logger = logging.getLogger(__name__)


class FilesEmptyTrashJobHandler:
    """Обрабатывает одну порцию ручной очистки с durable продолжением и проверкой lease."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Принимает фабрику worker-сессий без request-scoped ресурсов."""
        self._sessions = sessions

    async def handle(self, job: ScheduledJob) -> None:
        """Атомарно сохраняет доменные переходы, purge jobs и продолжение прохода."""
        if job.tenant_id is None or not job.lock_token or job.job_type != JOB_TYPE:
            raise ValueError("Invalid empty trash job envelope.")
        cutoff = datetime.fromisoformat(job.payload["cutoff"])
        if cutoff.utcoffset() is None or cutoff > datetime.now(UTC):
            raise ValueError("Empty trash cutoff must be an elapsed aware instant.")
        after_id = (
            UUID(job.payload["after_id"]) if job.payload.get("after_id") else None
        )
        command = EmptyTrashCommand(
            job.tenant_id, cutoff, after_id, job.payload.get("batch_size", 100)
        )
        try:
            async with TenantGate(self._sessions).hold(job.tenant_id) as connection:
                await bind_tenant_schema(
                    connection,
                    job.tenant_id,
                    TenantSchemaNaming(dnk_config.SCHEMA_PREFIX),
                )
                async with UnitOfWork(
                    async_sessionmaker(connection, expire_on_commit=False)
                ) as uow:
                    jobs = SqlAlchemyScheduledJobRepository(uow.session)
                    if not await jobs.owns_current_lease(
                        job_id=job.id,
                        tenant_id=job.tenant_id,
                        lock_token=job.lock_token,
                    ):
                        return
                    result = await build_files_handlers(
                        uow.session
                    ).empty_trash.execute(command)
                    if result.next_after_id is not None:
                        queue = ScheduledFilePurgeQueue(
                            ScheduleScheduledJobUseCase(
                                repository=jobs,
                                clock=UtcClock(),
                                uuid_generator=UUID7Generator(),
                            ),
                            jobs,
                        )
                        await queue.schedule_empty(
                            job.tenant_id,
                            uuid5(job.id, f"after:{result.next_after_id}"),
                            cutoff,
                            result.next_after_id,
                            command.batch_size,
                        )
                    if not await jobs.owns_current_lease(
                        job_id=job.id,
                        tenant_id=job.tenant_id,
                        lock_token=job.lock_token,
                        for_update=True,
                    ):
                        raise ScheduledJobDeferred(
                            "Empty trash lease is no longer current."
                        )
            logger.info(
                "Empty trash batch committed",
                extra={
                    "event": "files.trash.empty.committed",
                    "tenant_id": str(job.tenant_id),
                    "job_id": str(job.id),
                    "queued_count": result.queued_count,
                    "has_continuation": result.next_after_id is not None,
                },
            )
        except TenantUnavailable as error:
            raise ScheduledJobDeferred("Tenant admission unavailable.") from error
