from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from src.modules.catalog.domain.product.value_object.kind import ProductKind


class PutVariantStructureItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID | None = None
    sku_id: UUID


class PutVariantStructureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ProductKind
    variants: list[PutVariantStructureItemRequest] = Field(min_length=1)
