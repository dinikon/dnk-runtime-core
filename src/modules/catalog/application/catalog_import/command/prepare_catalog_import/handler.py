from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_import.repository import CatalogImportRepository
from src.modules.shared.domain.time.clock_port import ClockPort
from src.modules.catalog.application.catalog_import.staging_port import (
    ImportAnalysisPort,
)
from .command import PrepareCatalogImportCommand
from .dto import PrepareCatalogImportResultDTO


class PrepareCatalogImportHandler:
    """Отдельный сценарий prepare_catalog_import."""

    def __init__(
        self,
        repository: CatalogImportRepository,
        clock: ClockPort,
        staging: ImportAnalysisPort,
    ) -> None:
        """Получает порты финальной транзакции подготовки."""
        self.repository, self.clock = repository, clock
        self.staging = staging

    async def execute(
        self, command: PrepareCatalogImportCommand
    ) -> PrepareCatalogImportResultDTO:
        """Публикует полностью подготовленную версию источника."""
        entity = await self.repository.get(EntityIdVO(command.import_id), lock=True)
        if entity.version == command.version and entity.status == "preparing":
            entity.adopt_detected_configuration(command.configuration, self.clock.now())
            entity.prepared(command.total, self.clock.now())
            await self.staging.describe(command.import_id, command.analysis)
            await self.repository.save(entity)
        return PrepareCatalogImportResultDTO(entity.id.uuid, entity.status)
