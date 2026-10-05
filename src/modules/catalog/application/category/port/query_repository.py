from typing import Protocol

from src.modules.catalog.application.category.query.get_category.dto import (
    CategoryDetailsDTO,
)
from src.modules.catalog.application.category.query.list_categories.dto import (
    CategoryListItemDTO,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO


class CategoryQueryRepositoryProtocol(Protocol):
    async def get_details(
        self, category_id: CategoryIdVO, locale: CategoryLocaleVO
    ) -> CategoryDetailsDTO | None: ...
    async def list_all(
        self, locale: CategoryLocaleVO
    ) -> tuple[CategoryListItemDTO, ...]: ...
