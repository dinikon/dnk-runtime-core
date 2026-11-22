from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO


@dataclass(frozen=True, slots=True)
class PublicationRecord:
    """Минимальная read-side запись участия без восстановления агрегата."""

    id: UUID
    feed_id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    overrides_count: int


@dataclass(frozen=True, slots=True)
class PublicationPage:
    """Передаёт ограниченную страницу и отдельные счётчики участия."""

    items: tuple[PublicationRecord, ...]
    total: int
    counts: tuple[tuple[str, int], ...]


class PublicationQueryRepositoryProtocol(Protocol):
    """Читает состав напрямую без FeedPublication.restore."""

    async def get(self, identifier: UUID) -> PublicationRecord | None:
        """Читает одну сохранённую привязку."""
        ...

    async def list(
        self,
        feed_id: FeedIdVO,
        status: str | None,
        matched_ids: tuple[UUID, ...] | None,
        limit: int,
        offset: int,
    ) -> PublicationPage:
        """Пагинирует состав и поиск по согласованным ID владельца Catalog."""
        ...
