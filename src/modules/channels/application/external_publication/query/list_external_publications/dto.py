from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ListExternalPublicationsItemDTO:
    """Описывает core строки списка публикаций."""

    publication_id: UUID
    core_version: int
    connection_id: UUID
    resource_type: str
    external_id: str
    external_sku: str | None
    price: Decimal | None
    sale_price: Decimal | None
    currency: str | None
    quantity: Decimal | None
    stock_status: str
    title: str | None
    title_locale: str | None
    main_image_url: str | None
    source_updated_at: datetime | None
    warnings: tuple[str, ...]
    observed_revision: int
    first_seen_at: datetime
    last_seen_at: datetime
    last_import_run_id: UUID


@dataclass(frozen=True, slots=True)
class ListExternalPublicationsResultDTO:
    """Возвращает проекцию сценария list_external_publications."""

    items: tuple[ListExternalPublicationsItemDTO, ...]
    total: int
