from pydantic import BaseModel

from src.modules.catalog.application.attribute.query.list_attributes.dto import (
    AttributeDetailsDTO,
)
from src.modules.catalog.presentation.attribute.http.response.get_attribute import (
    GetAttributeResponse,
)


class ListAttributesResponse(BaseModel):
    items: list[GetAttributeResponse]

    @classmethod
    def from_dtos(
        cls, items: tuple[AttributeDetailsDTO, ...]
    ) -> "ListAttributesResponse":
        return cls(items=[GetAttributeResponse.from_dto(item) for item in items])
