from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.catalog.application.catalog_import.contracts import ImportQueuePort
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.domain.catalog_import.aggregate import TERMINAL
from .command import ProcessCatalogImportBatchCommand
from .dto import ProcessCatalogImportBatchResultDTO


class ProcessCatalogImportBatchHandler:
    """Отдельный сценарий process_catalog_import_batch."""

    def __init__(
        self,
        repository: CatalogImportRepository,
        queue: ImportQueuePort,
        clock: ClockPort,
    ) -> None:
        """Получает внешнюю транзакцию продолжения пачки."""
        self.repository, self.queue, self.clock = repository, queue, clock

    async def execute(
        self, command: ProcessCatalogImportBatchCommand
    ) -> ProcessCatalogImportBatchResultDTO:
        """Фиксирует остановку либо планирует продолжение с сохранённого курсора."""
        entity = await self.repository.get(EntityIdVO(command.import_id), lock=True)
        entity.stop(self.clock.now())
        if entity.status not in TERMINAL and entity.version == command.version:
            job_id = await self.queue.schedule(
                entity.id,
                entity.version,
                entity.processed,
                "run",
                generation=entity.generation,
            )
            entity.schedule(job_id, self.clock.now())
        await self.repository.save(entity)
        return ProcessCatalogImportBatchResultDTO(
            entity.id.uuid, entity.processed, entity.status in TERMINAL
        )
