from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from datetime import timedelta
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.catalog.domain.catalog_import.aggregate import EXECUTING, TERMINAL
from src.modules.catalog.domain.error import CatalogNotFoundError
from src.modules.catalog.application.catalog_import.maintenance_port import (
    ImportMaintenancePort,
)
from src.modules.catalog.application.catalog_import.contracts import ImportQueuePort
from .command import MaintainCatalogImportsCommand
from .dto import MaintainCatalogImportsResultDTO


class MaintainCatalogImportsHandler:
    """Сверяет состояния и сроки хранения отдельного запуска."""

    def __init__(
        self,
        repository: CatalogImportRepository,
        maintenance: ImportMaintenancePort,
        queue: ImportQueuePort,
        draft_hours: int,
        source_days: int,
        result_days: int,
    ) -> None:
        """Получает порты общей транзакции и instance-политику хранения."""
        self.repository, self.maintenance, self.queue = repository, maintenance, queue
        self.draft_hours, self.source_days, self.result_days = (
            draft_hours,
            source_days,
            result_days,
        )

    async def execute(
        self, command: MaintainCatalogImportsCommand
    ) -> MaintainCatalogImportsResultDTO:
        """Истекает черновик, сверяет исчерпанные jobs и очищает только технические данные."""
        try:
            entity = await self.repository.get(EntityIdVO(command.import_id), lock=True)
        except CatalogNotFoundError:
            return MaintainCatalogImportsResultDTO(0, 0, 0)
        expired = failed = 0
        if entity.status in {
            "preparing",
            "mapping",
        } and command.now - entity.created_at >= timedelta(hours=self.draft_hours):
            entity.expire(command.now)
            expired = 1
        elif (
            entity.status in EXECUTING | {"preparing"}
            and entity.job_id
            and await self.maintenance.job_terminal(entity.job_id.uuid)
        ):
            if entity.status == "cancelling":
                entity.stop(command.now)
            else:
                entity.fail(
                    "Фоновое задание завершилось без завершения импорта.", command.now
                )
                failed = 1
        if entity.status in TERMINAL and entity.finished_at:
            age = command.now - entity.finished_at
            if age >= timedelta(days=self.source_days) and (
                entity.source_file_id or entity.source_url
            ):
                source_id = entity.forget_source(command.now)
                await self.maintenance.clear_source(
                    entity.id.uuid,
                    source_id.uuid if source_id else None,
                    entity.actor_id.uuid,
                )
            if age >= timedelta(days=self.result_days):
                await self.maintenance.delete_results(entity.id.uuid)
                return MaintainCatalogImportsResultDTO(expired, failed, 1)
        await self.repository.save(entity)
        await self.queue.schedule(
            entity.id,
            0,
            int(command.now.timestamp()),
            "maintain",
            delay_seconds=86400 if entity.status in TERMINAL else 300,
        )
        return MaintainCatalogImportsResultDTO(expired, failed, 0)
