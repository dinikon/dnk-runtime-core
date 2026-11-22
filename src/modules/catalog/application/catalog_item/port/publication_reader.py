from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
from src.modules.catalog.application.catalog_item.port.calculation_reader import (
    CatalogCalculationReference,
)


@dataclass(frozen=True, slots=True)
class CatalogPublicationSubject:
    """Передаёт идентичность и подпись выбранной позиции без цены и ORM."""

    reference: CatalogCalculationReference
    kind: str
    sku: str | None
    title: str | None
    parent_title: str | None
    available: bool


class CatalogPublicationFamilyNotFoundError(Exception):
    """Сообщает об отсутствующем или архивном семействе."""


class CatalogPublicationSelectionError(Exception):
    """Отклоняет неверное семейство или слишком большой снимок выбора."""


class CatalogPublicationReaderProtocol(Protocol):
    """Владеет пакетным чтением идентичности, поиском и снимком вариантов."""

    async def read_many(
        self, references: tuple[CatalogCalculationReference, ...], locale: str
    ) -> tuple[CatalogPublicationSubject, ...]:
        """Возвращает найденные корректные пары, сохраняя архивную доступность отдельно."""
        ...

    async def search_ids(self, search: str, locale: str) -> tuple[UUID, ...]:
        """Возвращает только идентификаторы совпадений для серверного отбора потребителем."""
        ...

    async def variant_selection(
        self, root_id: UUID, locale: str
    ) -> tuple[CatalogPublicationSubject, ...]:
        """Фиксирует до ста текущих доступных вариантов одним чтением состава."""
        ...
