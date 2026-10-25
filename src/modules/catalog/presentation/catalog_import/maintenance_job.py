from datetime import UTC, datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.config import dnk_config
from src.modules.catalog.application.catalog_import.command.maintain_catalog_imports.command import (
    MaintainCatalogImportsCommand,
)
from src.modules.catalog.application.catalog_import.command.maintain_catalog_imports.handler import (
    MaintainCatalogImportsHandler,
)
from src.modules.catalog.infrastructure.catalog_import.repository import (
    SqlAlchemyCatalogImportRepository,
)
from src.modules.catalog.infrastructure.catalog_import.maintenance import (
    SqlAlchemyImportMaintenance,
)
from src.modules.catalog.presentation.catalog_import.assembly import build_import_queue
from src.modules.catalog.presentation.catalog_import.runtime import CatalogImportRuntime
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from uuid import UUID


class CatalogImportMaintenanceJobHandler:
    """Внешняя сборка периодической сверки и очистки отдельного импорта."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        """Принимает независимую worker factory."""
        self.sessions = sessions

    async def handle(self, job: ScheduledJob) -> None:
        """Сверяет один запуск под tenant admission и актуальной lease."""
        if (
            job.tenant_id is None
            or not job.lock_token
            or job.job_type != "catalog.import.maintain"
        ):
            raise ValueError("Invalid import maintenance envelope.")
        runtime = CatalogImportRuntime(self.sessions, job.tenant_id)
        settings = dnk_config.CATALOG_IMPORT
        async with runtime.transaction() as uow:
            await MaintainCatalogImportsHandler(
                SqlAlchemyCatalogImportRepository(uow.session),
                SqlAlchemyImportMaintenance(uow.session, job.tenant_id),
                build_import_queue(uow.session, job.tenant_id),
                settings.draft_hours,
                settings.source_days,
                settings.result_days,
            ).execute(
                MaintainCatalogImportsCommand(
                    UUID(job.payload["import_id"]), datetime.now(UTC)
                )
            )
            if not await build_scheduled_job_repository(uow.session).owns_current_lease(
                job_id=job.id,
                tenant_id=job.tenant_id,
                lock_token=job.lock_token,
                for_update=True,
            ):
                raise ScheduledJobDeferred("Import maintenance lease expired.")
