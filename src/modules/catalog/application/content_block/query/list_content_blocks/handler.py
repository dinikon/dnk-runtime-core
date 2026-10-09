from src.modules.catalog.application.port.mutation_lock import CatalogMutationLockPort

from src.modules.catalog.application.content_block.port.query_repository import (
    ContentBlockQueryRepositoryProtocol,
)

from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.content_block.query.list_content_blocks.query import (
    ListContentBlocksQuery,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.dto import (
    ListContentBlocksPageDTO,
)


class ListContentBlocksHandler:
    """Координирует list_content_blocks; инварианты и переходы принадлежат Domain."""

    def __init__(
        self,
        repository: ContentBlockQueryRepositoryProtocol,
        lock: CatalogMutationLockPort,
    ) -> None:
        """Принимает только необходимые этому сценарию порты."""
        self._repository = repository
        self._lock = lock

    async def execute(self, query: ListContentBlocksQuery) -> ListContentBlocksPageDTO:
        """Выполняет конкретный сценарий в контексте внешнего UoW."""
        await self._lock.acquire_read(query.tenant_id)
        LocaleVO(query.locale)
        if query.page < 1 or not 1 <= query.page_size <= 100:
            raise InvalidCatalogValueError("Некорректная пагинация.")
        return await self._repository.list_page(
            query.locale, query.search, query.page, query.page_size
        )
