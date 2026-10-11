from pydantic import BaseModel, ConfigDict


class CreateSimpleCatalogItemRequest(BaseModel):
    """Отдельное тело команды create_simple_catalog_item."""

    model_config = ConfigDict(extra="forbid")
    virtual: bool = False
