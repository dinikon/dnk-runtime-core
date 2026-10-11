from pydantic import BaseModel, ConfigDict, Field, StrictBool
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    ValueOverride,
)


class SetCatalogItemVirtualRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_virtual."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    virtual: ValueOverride[StrictBool]
