from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PublicationListItemDTO:
    """Передаёт строку списка публикаций без сырого снимка."""

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


@dataclass(frozen=True, slots=True)
class PublicationPageDTO:
    """Передаёт страницу сохранённых публикаций текущего подключения."""

    items: tuple[PublicationListItemDTO, ...]
    total: int
    offset: int
    limit: int
