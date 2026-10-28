from datetime import datetime
from pydantic import BaseModel
from src.modules.catalog.presentation.catalog_item.http.response.get_catalog_item import (
    CatalogItemDetailsResponse,
)


class GetCatalogVariantResponse(BaseModel):
    """Собственные и эффективные данные одной entity выбранной locale."""

    item: CatalogItemDetailsResponse
    as_of: datetime
