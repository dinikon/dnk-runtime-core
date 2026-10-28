"""Компоненты конкретных HTTP-ответов публикаций без нативных JSON."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.channels.application.external_publication.representation import (
    PublicationItemView,
    PublicationCardView,
)


class PublicationItemFields(BaseModel):
    """Перечисляет поддержанные публичные поля компонента ответа."""

    id: UUID
    external_id: str
    kind: str
    title: str | None
    sku: str | None
    url: str | None
    main_image_url: str | None
    price: str | None
    regular_price: str | None
    sale_price: str | None
    currency: str
    quantity: str | None
    stock_mode: str
    stock_source_publication_id: UUID
    availability: str | None
    status: str | None
    last_seen_at: datetime
    stale_configuration: bool

    @classmethod
    def from_view(cls, view: PublicationItemView) -> "PublicationItemFields":
        """Создаёт транспортный компонент из конкретной Application-проекции."""
        return cls(
            id=view.id,
            external_id=view.external_id,
            kind=view.kind,
            title=view.title,
            sku=view.sku,
            url=view.url,
            main_image_url=view.main_image_url,
            price=view.price,
            regular_price=view.regular_price,
            sale_price=view.sale_price,
            currency=view.currency,
            quantity=view.quantity,
            stock_mode=view.stock_mode,
            stock_source_publication_id=view.stock_source_publication_id,
            availability=view.availability,
            status=view.status,
            last_seen_at=view.last_seen_at,
            stale_configuration=view.stale_configuration,
        )


class PublicationCardFields(BaseModel):
    """Перечисляет поддержанные публичные поля компонента ответа."""

    id: UUID
    root_kind: str
    title: str | None
    selected_publication_id: UUID | None
    items: list[PublicationItemFields]
    min_price: str | None
    max_price: str | None
    currency: str | None
    last_seen_at: datetime
    root_external_id: str
    root_sku: str | None
    root_main_image_url: str | None

    @classmethod
    def from_view(cls, view: PublicationCardView) -> "PublicationCardFields":
        """Создаёт транспортный компонент из конкретной Application-проекции."""
        return cls(
            id=view.id,
            root_kind=view.root_kind,
            root_external_id=view.root_external_id,
            root_sku=view.root_sku,
            root_main_image_url=view.root_main_image_url,
            title=view.title,
            selected_publication_id=view.selected_publication_id,
            items=[PublicationItemFields.from_view(item) for item in view.items],
            min_price=view.min_price,
            max_price=view.max_price,
            currency=view.currency,
            last_seen_at=view.last_seen_at,
        )
