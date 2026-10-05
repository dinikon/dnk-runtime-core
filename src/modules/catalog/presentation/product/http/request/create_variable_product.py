from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.modules.catalog.presentation.product.http.request.create_product import (
    CreateProductContentRequest,
)


class CreateVariantSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    attribute_id: UUID = Field(strict=False)
    option_id: UUID = Field(strict=False)


class CreateVariableVariantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sku_id: UUID = Field(strict=False)
    selections: list[CreateVariantSelectionRequest] = Field(min_length=1, max_length=16)


class CreateVariableProductRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    variants: list[CreateVariableVariantRequest] = Field(min_length=2)
    contents: list[CreateProductContentRequest] = Field(default_factory=list)
