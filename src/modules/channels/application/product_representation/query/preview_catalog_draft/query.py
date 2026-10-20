from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PreviewCatalogDraftQuery:
    """Задаёт конкретный вход сценария preview_catalog_draft."""

    tenant_id: UUID
    actor_id: UUID
    publication_id: UUID
    expected_observed_revision: int
    locale: str
