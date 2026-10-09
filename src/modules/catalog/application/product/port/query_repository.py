from typing import Protocol
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.application.product.query.get_product.dto import (
    GetProductDetailsDTO,
)
from src.modules.catalog.application.product.query.list_products.dto import (
    ListProductsPageDTO,
)
from src.modules.catalog.application.product.query.get_variant.dto import (
    GetVariantDetailsDTO,
)


class ProductQueryRepositoryProtocol(Protocol):
    """Чтение отдельных use-case проекций без восстановления Domain."""

    async def get_details(
        self, identifier: ProductIdVO, locale: str
    ) -> GetProductDetailsDTO | None:
        """Возвращает карточку либо отсутствие объекта; перевод может быть null."""
        ...

    async def list_page(
        self,
        locale: str,
        search: str,
        page: int,
        page_size: int,
        product_type_id: ProductTypeIdVO | None = None,
    ) -> ListProductsPageDTO:
        """Возвращает стабильную страницу с серверным фильтром и количеством."""
        ...

    async def get_variant(
        self, product_id: ProductIdVO, variant_id: VariantIdVO, locale: str
    ) -> GetVariantDetailsDTO | None:
        """Читает внутреннюю позицию через оба ID без write repository позиции."""
        ...
