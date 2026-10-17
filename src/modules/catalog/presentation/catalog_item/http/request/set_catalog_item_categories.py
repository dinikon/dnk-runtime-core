from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class SetCatalogItemCategoriesRequest(BaseModel):
    """Отдельное тело команды set_catalog_item_categories."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
