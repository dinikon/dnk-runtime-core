from typing import Protocol
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO


class ClassificationReferencesPort(Protocol):
    """Проверяет tenant-ссылки без передачи справочных агрегатов в CatalogItem."""

    async def categories(
        self, identifiers: tuple[CategoryIdVO, ...]
    ) -> frozenset[CategoryIdVO]:
        """Читает существующие Category IDs."""
        ...

    async def tags(self, identifiers: tuple[TagIdVO, ...]) -> frozenset[TagIdVO]:
        """Читает существующие Tag IDs."""
        ...
