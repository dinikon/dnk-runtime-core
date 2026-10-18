from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class ListExternalPublicationsItemResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария list_external_publications."""

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


class ListExternalPublicationsResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария list_external_publications."""

    items: tuple[ListExternalPublicationsItemResponse, ...]
    total: int
