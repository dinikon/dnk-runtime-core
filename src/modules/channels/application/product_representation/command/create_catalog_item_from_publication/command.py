from dataclasses import dataclass
from uuid import UUID
from src.modules.channels.application.product_representation.contracts import (
    CatalogDraftValuesDTO,
)


@dataclass(frozen=True, slots=True)
class CreateCatalogItemFromPublicationCommand:
    """Задаёт конкретный вход сценария create_catalog_item_from_publication."""

    tenant_id: UUID
    actor_id: UUID
    publication_id: UUID
    expected_observed_revision: int
    request_key: UUID
    values: CatalogDraftValuesDTO

    preparation_id: UUID | None = None
    expected_preparation_revision: int | None = None
