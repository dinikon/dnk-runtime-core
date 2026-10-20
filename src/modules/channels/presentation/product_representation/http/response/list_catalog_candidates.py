from uuid import UUID
from pydantic import BaseModel


class ListCatalogCandidatesItemResponse(BaseModel):
    """Описывает строку выбора без внутренних Catalog DTO."""

    id: UUID
    title: str | None
    sku: str | None
    status: str
    can_bind: bool
    reason_code: str | None
    representation_revision: int | None


class ListCatalogCandidatesResponse(BaseModel):
    """Возвращает страницу поиска с причинами недоступности."""

    items: tuple[ListCatalogCandidatesItemResponse, ...]
    total: int
