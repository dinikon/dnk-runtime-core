from pydantic import BaseModel, ConfigDict

from src.modules.catalog.presentation.product_type.http.request.type_block import (
    TypeBlockRequest,
)


class PutTypeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_schema_version: int
    translations: dict[str, str]
    blocks: list[TypeBlockRequest]
