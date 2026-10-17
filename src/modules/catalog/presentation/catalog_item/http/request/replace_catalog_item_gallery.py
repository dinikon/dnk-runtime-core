from pydantic import BaseModel, ConfigDict, Field
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    GalleryValue,
)


class ReplaceCatalogItemGalleryRequest(BaseModel):
    """Отдельное тело команды replace_catalog_item_gallery."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    gallery: GalleryValue
