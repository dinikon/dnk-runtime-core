from pydantic import BaseModel
from datetime import datetime
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    ListItemResponse,
)


class ListCatalogVariantsResponse(BaseModel):
    """HTTP результат отдельного сценария list_catalog_items."""

    items: tuple[ListItemResponse, ...]
    total: int
    offset: int
    limit: int
    as_of: datetime
