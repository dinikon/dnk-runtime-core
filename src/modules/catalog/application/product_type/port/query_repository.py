from typing import Protocol
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.application.product_type.query.get_product_type.dto import (
    GetProductTypeDetailsDTO,
)
from src.modules.catalog.application.product_type.query.list_product_types.dto import (
    ListProductTypesPageDTO,
)


class ProductTypeQueryRepositoryProtocol(Protocol):
    """Чтение отдельных use-case проекций без восстановления Domain."""

    async def get_details(
        self, identifier: ProductTypeIdVO, locale: str
    ) -> GetProductTypeDetailsDTO | None:
        """Возвращает карточку либо отсутствие объекта; перевод может быть null."""
        ...

    async def list_page(
        self, locale: str, search: str, page: int, page_size: int
    ) -> ListProductTypesPageDTO:
        """Возвращает стабильную страницу с серверным фильтром и количеством."""
        ...
