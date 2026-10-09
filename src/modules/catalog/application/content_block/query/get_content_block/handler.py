from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.content_block.port.query_repository import (
    ContentBlockQueryRepositoryProtocol,
)

from src.modules.catalog.domain.content_block.error import ContentBlockNotFoundError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.content_block.query.get_content_block.query import (
    GetContentBlockQuery,
)
from src.modules.catalog.application.content_block.query.get_content_block.dto import (
    GetContentBlockDetailsDTO,
)


class GetContentBlockHandler:
    """Координирует get_content_block; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ContentBlockQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: GetContentBlockQuery) -> GetContentBlockDetailsDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        result = await self._repository.get_details(
            query.content_block_id, query.locale
        )
        if result is None:
            raise ContentBlockNotFoundError("Объект не найден.")
        return result
