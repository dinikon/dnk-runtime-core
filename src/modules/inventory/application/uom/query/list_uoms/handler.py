from src.modules.inventory.application.uom.query.list_uoms.dto import (
    ListUomsItemDTO,
    ListUomsResultDTO,
)
from src.modules.inventory.application.uom.query.list_uoms.query import ListUomsQuery
from src.modules.inventory.domain.uom_catalog import list_uoms


class ListUomsHandler:
    """Предоставляет системный Domain-справочник без инфраструктурного хранилища."""

    async def execute(self, query: ListUomsQuery) -> ListUomsResultDTO:
        """Создаёт проекцию всех разрешённых единиц из неизменяемого справочника."""
        return ListUomsResultDTO(
            items=tuple(
                ListUomsItemDTO(code=unit.code.value, dimension=unit.dimension)
                for unit in list_uoms()
            )
        )
