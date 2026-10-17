from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Self
from pydantic import BaseModel
from src.modules.channels.application.external_publication.query.list_publications.dto import (
    PublicationListItemDTO,
    PublicationPageDTO,
)


class PublicationListItemResponse(BaseModel):
    """Определяет HTTP поля сценария list_publications для PublicationListItemDTO."""

    id: UUID
    external_id: str
    title: str | None
    sku: str | None
    thumbnail_url: str | None
    price: Decimal | None
    currency: str | None
    availability: str | None
    source_status: str | None
    variations_count: int
    observed_at: datetime

    @classmethod
    def from_dto(cls, dto: PublicationListItemDTO) -> Self:
        """Явно переносит только разрешённые поля результата в HTTP ответ."""
        return cls(
            id=dto.id,
            external_id=dto.external_id,
            title=dto.title,
            sku=dto.sku,
            thumbnail_url=dto.thumbnail_url,
            price=dto.price,
            currency=dto.currency,
            availability=dto.availability,
            source_status=dto.source_status,
            variations_count=dto.variations_count,
            observed_at=dto.observed_at,
        )


class ListPublicationsResponse(BaseModel):
    """Определяет HTTP поля сценария list_publications для PublicationPageDTO."""

    items: tuple[PublicationListItemResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: PublicationPageDTO) -> Self:
        """Явно переносит только разрешённые поля результата в HTTP ответ."""
        return cls(
            items=tuple(
                PublicationListItemResponse.from_dto(value) for value in dto.items
            ),
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
