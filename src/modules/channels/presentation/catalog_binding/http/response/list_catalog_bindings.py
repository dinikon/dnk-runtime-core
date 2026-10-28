from pydantic import BaseModel, ConfigDict
from src.modules.channels.presentation.catalog_binding.http.response.fields import (
    GroupFields,
)


class ListCatalogBindingsResponse(BaseModel):
    """Публичный результат list_catalog_bindings."""

    model_config = ConfigDict(from_attributes=True)
    items: list[GroupFields]
    total: int
    offset: int
    limit: int
