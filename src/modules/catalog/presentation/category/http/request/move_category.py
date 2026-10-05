from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MoveCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    parent_id: UUID | None = Field(strict=False)
