from pydantic import BaseModel, ConfigDict, Field

from src.modules.catalog.presentation.product_type.http.request.type_block import (
    TypeBlockRequest,
)


class CreateTypeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    code: str
    translations: dict[str, str]
    blocks: list[TypeBlockRequest] = Field(default_factory=list)
