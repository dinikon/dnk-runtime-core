from pydantic import BaseModel, ConfigDict, Field
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    StockValue,
)


class SetCatalogItemStockRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_stock."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    stock: StockValue
