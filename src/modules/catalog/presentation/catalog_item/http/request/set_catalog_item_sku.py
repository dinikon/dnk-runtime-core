from pydantic import BaseModel, ConfigDict, Field


class SetCatalogItemSkuRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_sku."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    sku: str | None
