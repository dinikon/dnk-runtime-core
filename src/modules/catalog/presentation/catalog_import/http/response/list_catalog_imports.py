from pydantic import BaseModel
from src.modules.catalog.presentation.catalog_import.http.response.get_catalog_import import (
    CatalogImportSummaryResponse,
)


class ListCatalogImportsResponse(BaseModel):
    """Страница журнала импортов."""

    items: list[CatalogImportSummaryResponse]
    total: int
