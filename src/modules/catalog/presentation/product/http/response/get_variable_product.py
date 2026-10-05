from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.modules.catalog.application.product.query.get_product.dto import (
    ProductVariantDTO,
    VariableProductDetailsDTO,
)
from src.modules.catalog.presentation.product.http.response.get_product import (
    GetProductContentResponse,
)


class GetVariableSelectionResponse(BaseModel):
    attribute_id: UUID
    attribute_code: str
    attribute_name: str | None
    option_id: UUID
    option_code: str
    option_name: str | None


class GetVariableVariantResponse(BaseModel):
    id: UUID
    sku_id: UUID
    sku_code: str
    selections: list[GetVariableSelectionResponse]

    @classmethod
    def from_dto(cls, dto: ProductVariantDTO) -> "GetVariableVariantResponse":
        if dto.sku_code is None:
            raise ValueError("GetProductHandler must resolve every SKU code.")
        return cls(
            id=dto.id,
            sku_id=dto.sku_id,
            sku_code=dto.sku_code,
            selections=[
                GetVariableSelectionResponse(
                    attribute_id=selection.attribute_id,
                    attribute_code=selection.attribute_code,
                    attribute_name=selection.attribute_name,
                    option_id=selection.option_id,
                    option_code=selection.option_code,
                    option_name=selection.option_name,
                )
                for selection in dto.selections
            ],
        )


class GetVariableProductResponse(BaseModel):
    id: UUID
    type: str
    variants: list[GetVariableVariantResponse]
    requested_locale: str
    content_locales: list[str]
    content: GetProductContentResponse | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID

    @classmethod
    def from_dto(cls, dto: VariableProductDetailsDTO) -> "GetVariableProductResponse":
        return cls(
            id=dto.id,
            type=dto.type,
            variants=[
                GetVariableVariantResponse.from_dto(item) for item in dto.variants
            ],
            requested_locale=dto.requested_locale,
            content_locales=list(dto.content_locales),
            content=(
                GetProductContentResponse.from_dto(dto.content)
                if dto.content is not None
                else None
            ),
            created_at=dto.created_at,
            updated_at=dto.updated_at,
            created_by=dto.created_by,
            updated_by=dto.updated_by,
        )
