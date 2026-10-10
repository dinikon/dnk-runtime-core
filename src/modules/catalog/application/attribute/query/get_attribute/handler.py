from src.modules.catalog.application.attribute.port.query_repository import (
    AttributeQueryRepositoryProtocol,
)
from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort
from src.modules.catalog.domain.attribute.error import AttributeNotFoundError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.attribute.query.get_attribute.query import (
    GetAttributeQuery,
)
from src.modules.catalog.application.attribute.query.get_attribute.dto import (
    GetAttributeDetailsDTO,
)


class GetAttributeHandler:
    """Читает проекцию get_attribute без восстановления агрегата."""

    def __init__(
        self,
        repository: AttributeQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает порт проекций и согласованного чтения."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: GetAttributeQuery) -> GetAttributeDetailsDTO:
        """Проверяет параметры и возвращает собственный DTO сценария."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        result = await self._repository.get_details(query.attribute_id, query.locale)
        if result is None:
            raise AttributeNotFoundError("Характеристика отсутствует.")
        return result
