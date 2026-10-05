from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateCategoryTranslationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    locale: str
    name: str


class CreateCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    parent_id: UUID | None = Field(default=None, strict=False)
    translations: list[CreateCategoryTranslationRequest] = Field(min_length=1)
