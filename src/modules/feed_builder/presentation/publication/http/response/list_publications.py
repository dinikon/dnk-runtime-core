from datetime import datetime
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.feed_builder.application.publication.query.list_publications.dto import (
    PublicationListItemDTO,
    ListPublicationsResultDTO,
)


class PublicationListItemResponse(BaseModel):
    """Показывает идентичность участия и подпись источника без ложного READY."""

    id: UUID
    feed_id: UUID
    catalog_item_id: UUID
    catalog_variant_id: UUID | None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    overrides_count: int
    kind: str | None
    title: str | None
    parent_title: str | None
    sku: str | None
    source_available: bool

    @classmethod
    def from_dto(cls, item: PublicationListItemDTO) -> Self:
        """Явно собирает HTTP-представление строки состава."""
        r = item.record
        return cls(
            id=r.id,
            feed_id=r.feed_id,
            catalog_item_id=r.catalog_item_id,
            catalog_variant_id=r.catalog_variant_id,
            status=r.status,
            version=r.version,
            created_at=r.created_at,
            updated_at=r.updated_at,
            overrides_count=r.overrides_count,
            kind=item.kind,
            title=item.title,
            parent_title=item.parent_title,
            sku=item.sku,
            source_available=item.source_available,
        )


class ListPublicationsResponse(BaseModel):
    """Возвращает серверную страницу, контекст Feed и счётчики всех статусов."""

    feed_id: UUID
    feed_version: int
    feed_status: str
    items: tuple[PublicationListItemResponse, ...]
    total: int
    counts: dict[str, int]

    @classmethod
    def from_dto(cls, value: ListPublicationsResultDTO) -> Self:
        """Не отдаёт внутреннюю read-side запись напрямую."""
        return cls(
            feed_id=value.feed_id,
            feed_version=value.feed_version,
            feed_status=value.feed_status,
            items=tuple(PublicationListItemResponse.from_dto(i) for i in value.items),
            total=value.total,
            counts=dict(value.counts),
        )
