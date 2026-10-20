from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListCatalogCandidatesQuery:
    """Задаёт конкретный вход сценария list_catalog_candidates."""

    tenant_id: UUID
    publication_id: UUID
    locale: str
    search: str | None = None
    offset: int = 0
    limit: int = 20
