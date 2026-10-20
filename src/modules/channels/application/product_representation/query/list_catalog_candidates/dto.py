from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ListCatalogCandidatesItemDTO:
    """Описывает доступность выбора одного результата поиска Catalog."""

    id: UUID
    title: str | None
    sku: str | None
    status: str
    can_bind: bool
    reason_code: str | None
    representation_revision: int | None


@dataclass(frozen=True, slots=True)
class ListCatalogCandidatesResultDTO:
    """Возвращает конкретный результат сценария list_catalog_candidates."""

    items: tuple[ListCatalogCandidatesItemDTO, ...]
    total: int
