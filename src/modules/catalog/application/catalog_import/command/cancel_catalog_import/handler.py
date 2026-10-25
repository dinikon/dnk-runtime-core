from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.shared.domain.time.clock_port import ClockPort
from .command import CancelCatalogImportCommand
from .dto import CancelCatalogImportResultDTO


class CancelCatalogImportHandler:
    """Отдельный сценарий cancel_catalog_import."""

    def __init__(self, repository: CatalogImportRepository, clock: ClockPort) -> None:
        """Получает состояние текущего tenant и часы."""
        self.repository, self.clock = repository, clock

    async def execute(
        self, command: CancelCatalogImportCommand
    ) -> CancelCatalogImportResultDTO:
        """Запрашивает остановку без отката ранее сохранённых товаров."""
        entity = await self.repository.get(EntityIdVO(command.import_id), lock=True)
        entity.cancel(self.clock.now())
        await self.repository.save(entity)
        return CancelCatalogImportResultDTO(entity.id.uuid, entity.status)
