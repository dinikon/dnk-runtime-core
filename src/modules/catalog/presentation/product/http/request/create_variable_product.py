from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from src.modules.catalog.presentation.product.http.request.create_product import (
    CreateProductContentRequest,
)


class CreateVariableProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sku_ids: list[UUID] = Field(min_length=2, strict=False)
    contents: list[CreateProductContentRequest] = Field(default_factory=list)
    product_type_id: UUID | None = None
    schema_version: int | None = None
