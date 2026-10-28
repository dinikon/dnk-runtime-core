"""Чистая сборка одной карточки из нормализованных read-снимков."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.channels.application.external_publication.port.query_repository import (
    PublicationReadRow,
)
from src.modules.channels.domain.external_publication.error import (
    ExternalPublicationNotFoundError,
)
from src.modules.channels.domain.external_publication.value_object import (
    PublicationKind,
)


@dataclass(frozen=True, slots=True)
class PublicationItemView:
    """Публичная выбираемая позиция без raw_data и platform_data."""

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


@dataclass(frozen=True, slots=True)
class PublicationCardView:
    """Карточка Console с уже определённым составом продаваемых позиций."""

    id: UUID
    root_kind: str
    title: str | None
    selected_publication_id: UUID | None
    items: tuple[PublicationItemView, ...]
    min_price: str | None
    max_price: str | None
    currency: str | None
    last_seen_at: datetime
    root_external_id: str
    root_sku: str | None
    root_main_image_url: str | None


def build_card(
    *,
    root: PublicationReadRow,
    children: tuple[PublicationReadRow, ...],
    locale: str,
    config_revision: int,
    selected_id: UUID | None = None,
) -> PublicationCardView:
    """Включает продаваемый корень Prom и исключает контейнер WooCommerce."""
    members = (root, *children) if root.kind is PublicationKind.SIMPLE else children
    if (
        selected_id is not None
        and selected_id != root.id
        and not any(item.id == selected_id for item in members)
    ):
        raise ExternalPublicationNotFoundError("Позиция не принадлежит карточке.")
    selected = next(
        (item for item in members if item.id == selected_id),
        members[0] if members else None,
    )
    views = []
    for item in members:
        title = next(
            (
                translation.title
                for translation in item.data.titles
                if translation.locale == locale
            ),
            None,
        )
        if item.data.inherit_title:
            title = next(
                (
                    translation.title
                    for translation in root.data.titles
                    if translation.locale == locale
                ),
                None,
            )
        stock_source = root if item.data.stock_mode == "parent" else item
        views.append(
            PublicationItemView(
                item.id,
                item.external_id,
                item.kind.value,
                title,
                item.data.sku,
                item.data.url,
                item.data.main_image_url,
                str(item.data.price) if item.data.price is not None else None,
                (
                    str(item.data.regular_price)
                    if item.data.regular_price is not None
                    else None
                ),
                str(item.data.sale_price) if item.data.sale_price is not None else None,
                item.data.currency,
                (
                    str(stock_source.data.quantity)
                    if stock_source.data.quantity is not None
                    else None
                ),
                item.data.stock_mode,
                stock_source.id,
                item.data.availability,
                item.data.status,
                item.last_seen_at,
                item.observed_config_revision != config_revision
                or (
                    item.data.stock_mode == "parent"
                    and root.observed_config_revision != config_revision
                ),
            )
        )
    root_title = next(
        (
            translation.title
            for translation in root.data.titles
            if translation.locale == locale
        ),
        None,
    )
    selected_view = next(
        (item for item in views if selected is not None and item.id == selected.id),
        None,
    )
    prices = [item.data.price for item in members if item.data.price is not None]
    currencies = {item.data.currency for item in members if item.data.price is not None}
    return PublicationCardView(
        root.id,
        root.kind.value,
        (
            root_title
            if root.kind is PublicationKind.VARIABLE
            else selected_view.title if selected_view else root_title
        ),
        selected.id if selected else None,
        tuple(views),
        str(min(prices)) if prices and len(currencies) == 1 else None,
        str(max(prices)) if prices and len(currencies) == 1 else None,
        next(iter(currencies)) if len(currencies) == 1 else None,
        max(item.last_seen_at for item in (root, *children)),
        root.external_id,
        root.data.sku,
        root.data.main_image_url,
    )
