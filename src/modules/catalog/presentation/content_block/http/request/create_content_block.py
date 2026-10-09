from src.modules.catalog.domain.content_block.value_object.value_type import (
    ContentValueType,
)
from pydantic import BaseModel, ConfigDict, Field


class CreateContentBlockRequest(BaseModel):
    """Тело HTTP-сценария create_content_block; лишние поля отвергаются."""

    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    locale: str = Field(min_length=2, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    value_type: ContentValueType
