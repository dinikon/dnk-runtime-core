from pydantic import BaseModel, ConfigDict, Field
from src.modules.catalog.presentation.catalog_item.http.value_contracts import (
    MetadataValue,
)


class SetCatalogItemMetadataRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_metadata."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    metadata: tuple[MetadataValue, ...]
