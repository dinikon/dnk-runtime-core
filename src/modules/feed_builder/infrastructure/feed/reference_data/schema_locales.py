from src.modules.reference_data.application.port.catalog import CatalogRepositoryPort
from src.modules.feed_builder.application.feed.port.schema_locales import (
    SchemaLocaleDTO,
)


class ReferenceDataSchemaLocales:
    """Адаптирует публичный порт справочника, не читая чужие SQL-модели."""

    def __init__(self, catalog: CatalogRepositoryPort) -> None:
        """Принимает порт владельца, собранный на общем UoW."""
        self._catalog = catalog

    async def list_available(self) -> tuple[SchemaLocaleDTO, ...]:
        """Возвращает активные локали одним обращением к owner-контракту."""
        return tuple(
            SchemaLocaleDTO(str(item.code), item.name)
            for item in await self._catalog.list_locales()
        )
