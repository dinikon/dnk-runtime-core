from uuid import UUID
from sqlalchemy import update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.catalog_import import (
    CatalogImportModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_import_row import (
    CatalogImportRowModel,
)
from src.modules.files.application.stored_file.command.trash_file.command import (
    TrashFileCommand,
)
from src.modules.files.domain.error import FileNotFoundError
from src.modules.files.domain.stored_file.error import FileStateConflictError
from src.modules.files.infrastructure.assembly import build_files_handlers
from src.modules.shared.presentation.jobs.management import (
    build_scheduled_job_repository,
)


class SqlAlchemyImportMaintenance:
    """Адаптер общей очереди и публичных Files-сценариев."""

    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        """Получает сессию внешнего UoW и доверенный tenant."""
        self.session, self.tenant_id = session, tenant_id

    async def job_terminal(self, job_id: UUID) -> bool:
        """Использует публичный порт scheduler без его SQL-моделей."""
        return job_id in await build_scheduled_job_repository(
            self.session
        ).terminal_or_missing(tenant_id=self.tenant_id, job_ids=[job_id])

    async def clear_source(
        self, identifier: UUID, file_id: UUID | None, actor_id: UUID
    ) -> None:
        """Очищает исходные значения и source-файл, сохраняя результаты и галереи."""
        await self.session.execute(
            update(CatalogImportRowModel)
            .where(CatalogImportRowModel.import_id == identifier)
            .values(values={})
        )
        await self.session.execute(
            update(CatalogImportModel)
            .where(CatalogImportModel.id == identifier)
            .values(analysis={})
        )
        if file_id:
            try:
                await build_files_handlers(self.session).trash_file.execute(
                    TrashFileCommand(self.tenant_id, file_id, actor_id)
                )
            except (FileNotFoundError, FileStateConflictError):
                pass

    async def delete_results(self, identifier: UUID) -> None:
        """Удаляет технический журнал по FK cascade без Files delete."""
        await self.session.execute(
            delete(CatalogImportModel).where(CatalogImportModel.id == identifier)
        )
