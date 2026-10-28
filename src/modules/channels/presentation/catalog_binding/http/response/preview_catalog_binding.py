from pydantic import BaseModel, ConfigDict
from src.modules.channels.presentation.catalog_binding.http.response.fields import (
    PreviewFields,
)


class PreviewCatalogBindingResponse(BaseModel):
    """Публичный результат preview_catalog_binding."""

    model_config = ConfigDict(from_attributes=True)
    preview: PreviewFields
