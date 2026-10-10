from typing import Protocol
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO


class ClassificationReferencesPort(Protocol):
    """Предоставляет immutable наборы существующих ссылок в текущем tenant."""

    async def categories(
        self, identifiers: tuple[CategoryIdVO, ...]
    ) -> frozenset[CategoryIdVO]:
        """Проверяет наличие всех назначаемых категорий."""
        ...

    async def tags(self, identifiers: tuple[TagIdVO, ...]) -> frozenset[TagIdVO]:
        """Проверяет наличие всех назначаемых меток."""
        ...
