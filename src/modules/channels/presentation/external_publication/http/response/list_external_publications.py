from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class PublicationIdentityResponse(BaseModel):
    """Возвращает диагностическую проекцию без provider JSON."""

    state: str
    key: str | None
    conflict_count: int


class ListExternalPublicationsItemResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария list_external_publications."""

    publication_id: UUID
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
    catalog_item_id: UUID | None = None
    binding_id: UUID | None = None
    representation_id: UUID | None = None
    representation_revision: int | None = None
    export_enabled: bool = False

    identity: PublicationIdentityResponse | None = None


class ListPublicationIdentitySummaryResponse(BaseModel):
    """Возвращает сводку и инструкцию плагина для всего подключения."""

    label: str
    total: int
    missing: int
    duplicate: int
    valid: int
    duplicate_groups: int
    assessment: str
    checked_at: datetime | None
    scope_limitations: tuple[str, ...]
    help_title: str
    help_steps: tuple[str, ...]
    help_url: str
    recovery_verified: bool


class ListExternalPublicationsResponse(BaseModel):
    """Определяет отдельный HTTP-ответ сценария list_external_publications."""

    items: tuple[ListExternalPublicationsItemResponse, ...]
    total: int
    identity_summary: ListPublicationIdentitySummaryResponse | None = None
