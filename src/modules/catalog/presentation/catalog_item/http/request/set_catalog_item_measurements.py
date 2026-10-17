from pydantic import BaseModel, ConfigDict, Field
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    DimensionsValue,
    WeightValue,
)


class SetCatalogItemMeasurementsRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_measurements."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    weight: WeightValue | None
    dimensions: DimensionsValue | None
