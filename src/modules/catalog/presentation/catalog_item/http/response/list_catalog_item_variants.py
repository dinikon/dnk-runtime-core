from pydantic import BaseModel
from datetime import datetime
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    ReadItemResponse,
)


class ListCatalogItemVariantsResponse(BaseModel):
    """HTTP результат отдельного сценария list_catalog_item_variants."""

    items: tuple[ReadItemResponse, ...]
    total: int
    offset: int
    limit: int
    as_of: datetime
