from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MoveCategoryRequest(BaseModel):
    """Явный новый родитель, включая корень дерева."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    parent_id: UUID | None
