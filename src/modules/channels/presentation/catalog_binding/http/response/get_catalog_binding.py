from pydantic import BaseModel, ConfigDict
from src.modules.channels.presentation.catalog_binding.http.response.fields import (
    GroupFields,
)


class GetCatalogBindingResponse(BaseModel):
    """Публичный результат get_catalog_binding."""

    model_config = ConfigDict(from_attributes=True)
    binding: GroupFields
