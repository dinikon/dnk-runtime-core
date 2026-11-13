from src.modules.inventory.application.packaging_type.port.query_repository import (
    PackagingTypeQueryRepositoryProtocol,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.query import (
    GetPackagingTypeQuery,
)
from src.modules.inventory.application.packaging_type.query.get_packaging_type.dto import (
    GetPackagingTypeResultDTO,
)
from src.modules.inventory.domain.packaging_type.error import PackagingTypeNotFoundError


class GetPackagingTypeHandler:
    """Читает проекцию типа тары через отдельный Application-порт."""

    def __init__(self, repository: PackagingTypeQueryRepositoryProtocol) -> None:
        """Принимает read-порт без SQLAlchemy и управления транзакцией."""
        self._repository = repository

    async def execute(self, query: GetPackagingTypeQuery) -> GetPackagingTypeResultDTO:
        """Возвращает карточку или предметную ошибку отсутствия типа тары."""
        result = await self._repository.get_details(query)
        if result is None:
            raise PackagingTypeNotFoundError("Тип тары не найден.")
        return result
