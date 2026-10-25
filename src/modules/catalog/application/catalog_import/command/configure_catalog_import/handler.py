from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.catalog.application.catalog_import.contracts import ImportQueuePort
from src.modules.shared.domain.time.clock_port import ClockPort
from .command import ConfigureCatalogImportCommand
from .dto import ConfigureCatalogImportResultDTO


class ConfigureCatalogImportHandler:
    """Отдельный сценарий configure_catalog_import."""

    def __init__(
        self,
        repository: CatalogImportRepository,
        queue: ImportQueuePort,
        clock: ClockPort,
    ) -> None:
        """Получает зависимости общей транзакции."""
        self.repository, self.queue, self.clock = repository, queue, clock

    async def execute(
        self, command: ConfigureCatalogImportCommand
    ) -> ConfigureCatalogImportResultDTO:
        """Сохраняет версию черновика и планирует подготовку предпросмотра."""
        entity = await self.repository.get(EntityIdVO(command.import_id), lock=True)
        entity.configure(command.configuration, self.clock.now())
        job_id = await self.queue.schedule(entity.id, entity.version, 0, "prepare")
        entity.schedule(job_id, self.clock.now())
        await self.repository.save(entity)
        return ConfigureCatalogImportResultDTO(
            entity.id.uuid, entity.version, entity.status
        )
