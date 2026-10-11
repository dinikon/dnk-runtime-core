from pydantic import BaseModel
from datetime import datetime
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    ReadItemResponse,
)


class GetCatalogItemResponse(BaseModel):
    """HTTP результат отдельного сценария get_catalog_item."""

    item: ReadItemResponse
    as_of: datetime
