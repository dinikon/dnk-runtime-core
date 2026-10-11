from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class SetCatalogItemTagsRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_tags."""

    model_config = ConfigDict(extra="forbid")
    expected_root_revision: int = Field(ge=1)
    tag_ids: tuple[UUID, ...]
