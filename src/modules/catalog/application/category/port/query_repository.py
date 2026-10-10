from typing import Protocol
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.application.category.query.get_category.dto import (
    GetCategoryDetailsDTO,
)
from src.modules.catalog.application.category.query.list_categories.dto import (
    ListCategoriesPageDTO,
)


class CategoryQueryRepositoryProtocol(Protocol):
    """Чтение отдельных проекций enum-справочника."""

    async def get_details(
        self, identifier: CategoryIdVO, locale: str
    ) -> GetCategoryDetailsDTO | None:
        """Читает определение с options и явной locale без fallback."""
        ...

    async def list_page(
        self,
        locale: str,
        search: str,
        page: int,
        page_size: int,
        parent_id: CategoryIdVO | None,
        roots_only: bool,
    ) -> ListCategoriesPageDTO:
        """Возвращает страницу определений с устойчивым порядком."""
        ...
