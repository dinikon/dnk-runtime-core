from typing import Protocol
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.application.content_block.query.get_content_block.dto import (
    GetContentBlockDetailsDTO,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.dto import (
    ListContentBlocksPageDTO,
)


class ContentBlockQueryRepositoryProtocol(Protocol):
    """Чтение отдельных use-case проекций без восстановления Domain."""

    async def get_details(
        self, identifier: ContentBlockIdVO, locale: str
    ) -> GetContentBlockDetailsDTO | None:
        """Возвращает карточку либо отсутствие объекта; перевод может быть null."""
        ...

    async def list_page(
        self, locale: str, search: str, page: int, page_size: int
    ) -> ListContentBlocksPageDTO:
        """Возвращает стабильную страницу с серверным фильтром и количеством."""
        ...
