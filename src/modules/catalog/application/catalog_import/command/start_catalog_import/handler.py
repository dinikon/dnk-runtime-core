from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.catalog.application.catalog_import.contracts import ImportQueuePort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.catalog_import.concurrency_policy import (
    CatalogImportConcurrencyPolicy,
)
from .command import StartCatalogImportCommand
from .dto import StartCatalogImportResultDTO


class StartCatalogImportHandler:
    """Отдельный сценарий start_catalog_import."""

    def __init__(
        self,
        repository: CatalogImportRepository,
        queue: ImportQueuePort,
        clock: ClockPort,
        max_active: int,
    ) -> None:
        """Получает порты общей транзакции запуска."""
        self.repository, self.queue, self.clock = repository, queue, clock
        self.policy = CatalogImportConcurrencyPolicy(max_active)

    async def execute(
        self, command: StartCatalogImportCommand
    ) -> StartCatalogImportResultDTO:
        """Атомарно замораживает настройки и создаёт единственное задание."""
        await self.repository.lock_lane()
        entity = await self.repository.get(EntityIdVO(command.import_id), lock=True)
        if entity.start(command.version, self.clock.now()):
            self.policy.ensure_capacity(
                await self.repository.count_executing(entity.id)
            )
            job_id = await self.queue.schedule(entity.id, entity.version, 0, "run")
            entity.schedule(job_id, self.clock.now())
            await self.repository.save(entity)
        return StartCatalogImportResultDTO(entity.id.uuid, entity.status)
