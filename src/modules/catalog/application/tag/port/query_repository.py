from typing import Protocol
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.application.tag.query.get_tag.dto import (
    GetTagDetailsDTO,
)
from src.modules.catalog.application.tag.query.list_tags.dto import (
    ListTagsPageDTO,
)


class TagQueryRepositoryProtocol(Protocol):
    """Чтение отдельных проекций enum-справочника."""

    async def get_details(
        self, identifier: TagIdVO, locale: str
    ) -> GetTagDetailsDTO | None:
        """Читает определение с options и явной locale без fallback."""
        ...

    async def list_page(
        self, locale: str, search: str, page: int, page_size: int
    ) -> ListTagsPageDTO:
        """Возвращает страницу определений с устойчивым порядком."""
        ...
