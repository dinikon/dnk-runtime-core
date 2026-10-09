from src.modules.catalog.domain.content_block.value_object.value_type import (
    ContentValueType,
)
from pydantic import BaseModel, ConfigDict, Field


class UpdateContentBlockRequest(BaseModel):
    """Тело HTTP-сценария update_content_block; лишние поля отвергаются."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    locale: str = Field(min_length=2, max_length=64)
    label: str = Field(min_length=1, max_length=255)
    value_type: ContentValueType
