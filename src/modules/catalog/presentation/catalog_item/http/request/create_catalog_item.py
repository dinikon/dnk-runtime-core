from pydantic import BaseModel, ConfigDict


class CreateCatalogItemRequest(BaseModel):
    """Отдельное тело команды create_catalog_item."""

    model_config = ConfigDict(extra="forbid")
    virtual: bool = False
