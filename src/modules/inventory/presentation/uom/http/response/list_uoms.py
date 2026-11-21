from typing import Self

from pydantic import BaseModel

from src.modules.inventory.application.uom.query.list_uoms.dto import ListUomsResultDTO
from src.modules.inventory.domain.value_object.uom_dimension import UomDimension


class ListUomsItemResponse(BaseModel):
    """Описывает код и размерность доступной единицы учёта."""

    code: str
    dimension: UomDimension


class ListUomsResponse(BaseModel):
    """Описывает HTTP-ответ системного справочника единиц."""

    items: tuple[ListUomsItemResponse, ...]

    @classmethod
    def from_dto(cls, dto: ListUomsResultDTO) -> Self:
        """Явно преобразует результат Application в ответ справочника."""
        return cls(
            items=tuple(
                ListUomsItemResponse(code=item.code, dimension=item.dimension)
                for item in dto.items
            )
        )
