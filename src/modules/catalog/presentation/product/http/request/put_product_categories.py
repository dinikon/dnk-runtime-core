from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PutProductCategoriesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    category_ids: list[Annotated[UUID, Field(strict=False)]]
    primary_category_id: UUID | None = Field(strict=False)
