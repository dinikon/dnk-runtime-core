from typing import Protocol

from src.modules.inventory.application.packaging_type.query.get_packaging_type.query import (
    GetPackagingTypeQuery,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.dto import (
    GetPackagingTypeResultDTO,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.query import (
    ListPackagingTypesQuery,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.dto import (
    ListPackagingTypesResultDTO,
)


class PackagingTypeQueryRepositoryProtocol(Protocol):
    """Определяет чтение конкретных DTO без восстановления агрегата."""

    async def get_details(
        self, query: GetPackagingTypeQuery
    ) -> GetPackagingTypeResultDTO | None:
        """Возвращает карточку текущего tenant либо None."""
        ...

    async def list(self, query: ListPackagingTypesQuery) -> ListPackagingTypesResultDTO:
        """Возвращает страницу с едиными фильтрами total и строк."""
        ...
