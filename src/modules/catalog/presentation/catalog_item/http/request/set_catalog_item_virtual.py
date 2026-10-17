from pydantic import BaseModel, ConfigDict, Field, StrictBool


class SetCatalogItemVirtualRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_virtual."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    virtual: StrictBool
