from src.modules.catalog.application.catalog_item.command.update_catalog_item.command import (
    UpdateCatalogItemCommand,
)
from src.modules.catalog.application.catalog_item.command.update_catalog_item.dto import (
    UpdateCatalogItemResultDTO,
)
from src.modules.catalog.application.catalog_item.mutation_service import (
    CatalogItemMutationService,
)
from src.modules.catalog.application.catalog_item.port.content_schema import (
    CatalogItemContentSchemaPort,
)
from src.modules.catalog.application.catalog_item.port.files import (
    CatalogImageFilesPort,
)
from src.modules.catalog.application.port.currencies import CurrencyPort
from src.modules.catalog.application.port.locales import LocalePort
from src.modules.catalog.application.port.rich_text import RichTextSanitizerPort
from src.modules.catalog.application.catalog_item.update_service import (
    CatalogItemUpdateService,
)
from src.modules.shared.domain.time.clock_port import ClockPort


class UpdateCatalogItemHandler:
    """Выполняет HTTP-сценарий через общую подготовку обновлений."""

    def __init__(
        self,
        mutations: CatalogItemMutationService,
        clock: ClockPort,
        locales: LocalePort,
        schemas: CatalogItemContentSchemaPort,
        sanitizer: RichTextSanitizerPort,
        currencies: CurrencyPort,
        files: CatalogImageFilesPort,
    ) -> None:
        """Подключает сервис той же транзакции без вложенного handler."""
        self._service = CatalogItemUpdateService(
            mutations, clock, locales, schemas, sanitizer, currencies, files
        )

    async def execute(
        self, command: UpdateCatalogItemCommand
    ) -> UpdateCatalogItemResultDTO:
        """Сохраняет существующий контракт атомарного PATCH."""
        return await self._service.apply(command)
