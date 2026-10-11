from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    ValueOverride,
    DimensionsValue,
)


class SetCatalogItemMeasurementsRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_measurements."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    weight: ValueOverride[Decimal]
    dimensions: ValueOverride[DimensionsValue]
