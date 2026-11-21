from dataclasses import replace

from src.modules.inventory.application.packaging_type.port.query_repository import (
    PackagingTypeQueryRepositoryProtocol,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.query import (
    ListPackagingTypesQuery,
)
from src.modules.inventory.application.packaging_type.query.list_packaging_types.dto import (
    ListPackagingTypesResultDTO,
)


class ListPackagingTypesHandler:
    """Читает страницу справочника через Application-порт проекций."""

    def __init__(self, repository: PackagingTypeQueryRepositoryProtocol) -> None:
        """Принимает read-порт текущего tenant без инфраструктурных типов."""
        self._repository = repository

    async def execute(
        self, query: ListPackagingTypesQuery
    ) -> ListPackagingTypesResultDTO:
        """Убирает внешние пробелы поиска, сохраняя регистр и остальные фильтры."""
        search = query.search.strip() if query.search is not None else None
        return await self._repository.list(replace(query, search=search or None))
