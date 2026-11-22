from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
from src.modules.feed_builder.domain.publication.value_object.catalog_product_reference import (
    CatalogProductReferenceVO,
)


@dataclass(frozen=True, slots=True)
class PublicationCatalogSubject:
    """Передаёт минимальные факты Catalog в собственном контракте FeedBuilder."""

    reference: CatalogProductReferenceVO
    kind: str
    sku: str | None
    title: str | None
    parent_title: str | None
    available: bool


class PublicationSourceNotFoundError(Exception):
    """Сообщает о неверной или недоступной выбранной позиции."""


class PublicationSourceUnavailableError(Exception):
    """Отделяет техническую недоступность от отсутствующей позиции."""


class PublicationSelectionLimitError(Exception):
    """Сообщает об отклонённом снимке выбора вариантов."""


class PublicationCatalogReaderProtocol(Protocol):
    """Изолирует выбор и подписи Catalog от Application публикаций."""

    async def read_many(
        self, references: tuple[CatalogProductReferenceVO, ...], locale: str
    ) -> tuple[PublicationCatalogSubject, ...]:
        """Читает подписи и доступность пакетом."""
        ...

    async def search_ids(self, search: str, locale: str) -> tuple[UUID, ...]:
        """Возвращает IDs совпадений без импорта чужого ORM."""
        ...

    async def variant_selection(
        self, root_id: UUID, locale: str
    ) -> tuple[PublicationCatalogSubject, ...]:
        """Фиксирует ограниченный состав текущих вариантов."""
        ...
