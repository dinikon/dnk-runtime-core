from dataclasses import dataclass
from uuid import UUID
from src.modules.feed_builder.application.publication.port.query_repository import (
    PublicationRecord,
)


@dataclass(frozen=True, slots=True)
class PublicationListItemDTO:
    """Соединяет сохранённое участие с текущей безопасной подписью Catalog."""

    record: PublicationRecord
    kind: str | None
    title: str | None
    parent_title: str | None
    sku: str | None
    source_available: bool


@dataclass(frozen=True, slots=True)
class ListPublicationsResultDTO:
    """Возвращает серверную страницу состава с актуальным состоянием Feed."""

    feed_id: UUID
    feed_version: int
    feed_status: str
    items: tuple[PublicationListItemDTO, ...]
    total: int
    counts: tuple[tuple[str, int], ...]
