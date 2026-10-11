from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class SetCatalogItemPrimaryImageRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_primary_image."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    image_id: UUID
