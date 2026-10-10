import logging
from datetime import UTC, datetime, timedelta
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.files.application.stored_file.command.cleanup_orphaned_objects.command import (
    CleanupOrphanedObjectsCommand,
)
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel
from src.modules.tenancy.application.tenant.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.tenancy.domain.tenant.value_object.tenant_id import TenantIdVO
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_connection import (
    bind_tenant_schema,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_gate import TenantGate

from src.modules.files.infrastructure.jobs import JOB_TYPE, schedule_cleanup

logger = logging.getLogger(__name__)


class FilesCleanupJobHandler:
    """Внешняя сборка очистки orphaned объектов в tenant UoW."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Принимает фабрику worker-сессий, не связанную с HTTP-запросом."""
        self._sessions = sessions

    async def handle(self, job: ScheduledJob) -> None:
        """Открывает admission и tenant-сессию на время очистки."""
        if job.tenant_id is None:
            raise RuntimeError("File cleanup requires a tenant.")
        async with TenantGate(self._sessions).hold(job.tenant_id) as connection:
            await bind_tenant_schema(
                connection, job.tenant_id, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
            )
            async with AsyncSession(connection, expire_on_commit=False) as session:
                result = await build_files_handlers(session).cleanup.execute(
                    CleanupOrphanedObjectsCommand(
                        job.tenant_id, datetime.now(UTC) - timedelta(hours=24)
                    )
                )
                await session.commit()
                logger.info(
                    "File storage cleanup committed",
                    extra={
                        "event": "files.cleanup.committed",
                        "tenant_id": str(job.tenant_id),
                        "job_id": str(job.id),
                        "removed_objects": result.removed_objects,
                        "aborted_uploads": result.aborted_uploads,
                    },
                )


async def ensure_cleanup_jobs(
    sessions: async_sessionmaker[AsyncSession], stamp: datetime
) -> None:
    """Регистрирует hourly jobs только для подготовленных tenant-схем."""
    async with sessions() as lookup:
        identifiers = list(
            await lookup.scalars(
                select(TenantModel.id).where(
                    TenantModel.status.in_(["active", "freeze"])
                )
            )
        )
    naming = TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    for identifier in identifiers:
        try:
            async with TenantGate(sessions).hold(identifier) as connection:
                schema = naming.schema_name(TenantIdVO.from_value(identifier))
                if not await connection.scalar(
                    text("SELECT to_regclass(:name)"),
                    {"name": f"{schema}.files_buckets"},
                ):
                    continue
                await bind_tenant_schema(connection, identifier, naming)
                async with AsyncSession(connection, expire_on_commit=False) as session:
                    await schedule_cleanup(session, identifier, stamp)
                    await session.commit()
        except Exception:
            # Один недоступный tenant не блокирует регистрацию jobs остальных.
            logger.warning(
                "File cleanup scheduling failed",
                extra={
                    "event": "files.cleanup.schedule_failed",
                    "tenant_id": str(identifier),
                },
            )
