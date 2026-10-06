from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.catalog.domain.product_type.aggregate import ContentScope


class TypeBlockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    block_id: UUID = Field(strict=False)
    scope: ContentScope = Field(strict=False)
    required: bool
    position: int
