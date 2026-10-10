from src.modules.catalog.application.tag.port.query_repository import (
    TagQueryRepositoryProtocol,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.domain.tag.error import TagNotFoundError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.tag.query.get_tag.query import (
    GetTagQuery,
)
from src.modules.catalog.application.tag.query.get_tag.dto import (
    GetTagDetailsDTO,
)


class GetTagHandler:
    """Читает проекцию get_tag без восстановления агрегата."""

    def __init__(
        self,
        repository: TagQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает порт проекций и согласованного чтения."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: GetTagQuery) -> GetTagDetailsDTO:
        """Проверяет параметры и возвращает собственный DTO сценария."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        result = await self._repository.get_details(query.tag_id, query.locale)
        if result is None:
            raise TagNotFoundError("Характеристика отсутствует.")
        return result
