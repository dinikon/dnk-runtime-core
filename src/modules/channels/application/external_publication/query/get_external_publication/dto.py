from src.modules.channels.application.external_publication.identity_contract import (
    PublicationIdentityDiagnosticDTO,
)
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class GetExternalPublicationResultDTO:
    """Возвращает проекцию сценария get_external_publication."""

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
    identity: PublicationIdentityDiagnosticDTO | None = None
