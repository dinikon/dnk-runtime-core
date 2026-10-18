import logging
from time import perf_counter
from src.modules.files.infrastructure.stored_file.jobs.metrics import (
    purge_deliveries,
    purge_duration,
)
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.files.application.stored_file.command.purge_file.command import (
    PurgeFileCommand,
)
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.shared.infrastructure.persistence.unit_of_work.sqlalchemy import (
    UnitOfWork,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.tenancy.application.tenant.tenant_admission import TenantUnavailable
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate

JOB_TYPE = "files.purge"
logger = logging.getLogger(__name__)


class FilesPurgeJobHandler:
    """Внешняя сборка физического удаления с admission, write lock и fencing lease."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Принимает отдельную фабрику worker, без живого HTTP-контекста."""
        self._sessions = sessions

    async def handle(self, job: ScheduledJob) -> None:
        """Удаляет owned-версии и коммитит реестр только при актуальной worker lease."""
        if job.tenant_id is None or not job.lock_token or job.job_type != JOB_TYPE:
            raise ValueError("Invalid file purge job envelope.")
        if (
            UUID(job.payload["tenant_id"]) != job.tenant_id
            or UUID(job.payload["job_id"]) != job.id
        ):
            raise ValueError("File purge job IDs do not match envelope.")
        command = PurgeFileCommand(job.tenant_id, UUID(job.payload["file_id"]), job.id)
        started = perf_counter()
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
                        purge_deliveries.labels("stale").inc()
                        return
                    await build_files_handlers(uow.session).purge_file.execute(command)
                    # FOR UPDATE берётся после SDK, чтобы heartbeat мог продлевать долгую операцию.
                    if not await jobs.owns_current_lease(
                        job_id=job.id,
                        tenant_id=job.tenant_id,
                        lock_token=job.lock_token,
                        for_update=True,
                    ):
                        raise ScheduledJobDeferred(
                            "File purge lease is no longer current."
                        )
            purge_deliveries.labels("committed").inc()
            logger.info(
                "File purge committed",
                extra={
                    "event": "files.purge.committed",
                    "tenant_id": str(job.tenant_id),
                    "job_id": str(job.id),
                    "file_id": str(command.file_id),
                },
            )
        except TenantUnavailable as error:
            purge_deliveries.labels("deferred").inc()
            raise ScheduledJobDeferred("Tenant admission unavailable.") from error
        except ScheduledJobDeferred:
            purge_deliveries.labels("deferred").inc()
            raise
        except Exception:
            outcome = (
                "exhausted"
                if job.attempts >= dnk_config.SCHEDULED_JOBS.max_attempts
                else "retryable_failure"
            )
            purge_deliveries.labels(outcome).inc()
            raise
        finally:
            purge_duration.observe(perf_counter() - started)
