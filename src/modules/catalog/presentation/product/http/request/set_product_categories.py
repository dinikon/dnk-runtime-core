from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SetProductCategoriesRequest(BaseModel):
    """Полная замена categories в отдельном HTTP-сценарии."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    category_ids: tuple[UUID, ...]
    primary_category_id: UUID | None
