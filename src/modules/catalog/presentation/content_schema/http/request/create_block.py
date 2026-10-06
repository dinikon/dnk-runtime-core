from pydantic import BaseModel, ConfigDict, Field

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)


class CreateBlockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    code: str
    type: ContentBlockType = Field(strict=False)
    translations: dict[str, str]
