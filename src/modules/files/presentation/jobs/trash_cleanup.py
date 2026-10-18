import logging
from datetime import UTC, datetime
from uuid import UUID, uuid5
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.files.application.stored_file.command.cleanup_expired_trash.command import (
    CleanupExpiredTrashCommand,
)
from src.modules.files.infrastructure.stored_file.persistence.query_repository import (
    SqlAlchemyStoredFileQueryRepository,
)
from src.modules.files.infrastructure.stored_file.jobs.metrics import (
    observe_backlog,
    trash_queued,
)
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.files.infrastructure.jobs import (
    TRASH_CLEANUP_JOB_TYPE as JOB_TYPE,
    schedule_trash_cleanup,
)
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
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
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
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate

logger = logging.getLogger(__name__)


class FilesTrashCleanupJobHandler:
    """Собирает одну порцию корзины и её durable continuation на общем UoW."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Принимает фабрику worker-сессий, не связанную с запросом пользователя."""
        self._sessions = sessions

    async def handle(self, job: ScheduledJob) -> None:
        """Сохраняет задания, курсор и неизменный cutoff до атомарного commit порции."""
        if job.tenant_id is None or not job.lock_token or job.job_type != JOB_TYPE:
            raise ValueError("Invalid trash cleanup job envelope.")
        cutoff = datetime.fromisoformat(job.payload["cutoff"])
        if cutoff.utcoffset() is None or cutoff > datetime.now(UTC):
            raise ValueError("Trash cleanup cutoff must be an elapsed aware instant.")
        after_id = (
            UUID(job.payload["after_id"]) if job.payload.get("after_id") else None
        )
        command = CleanupExpiredTrashCommand(
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
                    jobs = build_scheduled_job_repository(uow.session)
                    if not await jobs.owns_current_lease(
                        job_id=job.id,
                        tenant_id=job.tenant_id,
                        lock_token=job.lock_token,
                    ):
                        return
                    result = await build_files_handlers(
                        uow.session
                    ).cleanup_trash.execute(command)
                    if result.next_after_id is not None:
                        queue = ScheduledFilePurgeQueue(
                            ScheduleScheduledJobUseCase(
                                repository=jobs,
                                clock=UtcClock(),
                                uuid_generator=UUID7Generator(),
                            ),
                            jobs,
                        )
                        await queue.schedule_cleanup(
                            job.tenant_id,
                            uuid5(job.id, f"after:{result.next_after_id}"),
                            cutoff,
                            result.next_after_id,
                            command.batch_size,
                        )
                    backlog = await SqlAlchemyStoredFileQueryRepository(
                        uow.session
                    ).cleanup_backlog(cutoff)
                    if not await jobs.owns_current_lease(
                        job_id=job.id,
                        tenant_id=job.tenant_id,
                        lock_token=job.lock_token,
                        for_update=True,
                    ):
                        raise ScheduledJobDeferred(
                            "Trash cleanup lease is no longer current."
                        )
            observe_backlog(job.tenant_id, backlog, datetime.now(UTC))
            trash_queued.labels("new").inc(result.queued_count)
            trash_queued.labels("recovery").inc(result.requeued_count)
            logger.info(
                "Trash cleanup batch committed",
                extra={
                    "event": "files.trash.cleanup.committed",
                    "tenant_id": str(job.tenant_id),
                    "job_id": str(job.id),
                    "queued_count": result.queued_count,
                    "requeued_count": result.requeued_count,
                    "has_continuation": result.next_after_id is not None,
                },
            )
        except TenantUnavailable as error:
            raise ScheduledJobDeferred("Tenant admission unavailable.") from error


async def ensure_trash_cleanup_jobs(
    sessions: async_sessionmaker[AsyncSession], stamp: datetime
) -> None:
    """Регистрирует hourly проходы старых и новых подготовленных tenant под штатным gate."""
    naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    after_id: UUID | None = None
    while True:
        async with sessions() as lookup:
            statement = select(TenantModel.id).where(
                TenantModel.status.in_(["active", "freeze"])
            )
            if after_id is not None:
                statement = statement.where(TenantModel.id > after_id)
            identifiers = tuple(
                await lookup.scalars(statement.order_by(TenantModel.id).limit(100))
            )
        if not identifiers:
            return
        for identifier in identifiers:
            try:
                async with TenantGate(sessions).hold(identifier) as connection:
                    schema = naming.schema_name(TenantIdVO.from_value(identifier))
                    if not await connection.scalar(
                        text("SELECT to_regclass(:name)"),
                        {"name": f"{schema}.files_registry"},
                    ):
                        continue
                    # Завершаем lookup-транзакцию, чтобы commit UoW фиксировал INSERT jobs.
                    await connection.commit()
                    await bind_tenant_schema(connection, identifier, naming)
                    async with UnitOfWork(
                        async_sessionmaker(connection, expire_on_commit=False)
                    ) as uow:
                        await schedule_trash_cleanup(uow.session, identifier, stamp)
            except TenantUnavailable:
                logger.debug(
                    "Trash cleanup registration deferred",
                    extra={
                        "event": "files.trash.cleanup.deferred",
                        "tenant_id": str(identifier),
                    },
                )
            except Exception as error:
                # Секреты SQL/SDK и строки исключений не попадают в registrar log.
                logger.warning(
                    "Trash cleanup registration failed",
                    extra={
                        "event": "files.trash.cleanup.schedule_failed",
                        "tenant_id": str(identifier),
                        "error_type": type(error).__name__,
                    },
                )
        after_id = identifiers[-1]
