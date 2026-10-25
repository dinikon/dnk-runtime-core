from uuid import UUID
from pydantic import BaseModel


class CatalogImportRowResponse(BaseModel):
    """Результат одной записи без полного содержимого товара."""

    number: int
    outcome: str
    sku: str | None
    item_id: UUID | None
    errors: list[str]
    warnings: list[str]


class ListCatalogImportRowsResponse(BaseModel):
    """Страница результатов с отдельными предупреждениями."""

    items: list[CatalogImportRowResponse]
    total: int
