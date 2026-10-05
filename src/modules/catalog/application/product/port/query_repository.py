from typing import Protocol

from src.modules.catalog.application.product.query.get_product.dto import (
    ProductDetailsDTO,
)
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO


class ProductQueryRepositoryProtocol(Protocol):
    """Проекция SIMPLE-карточки в привязанной к tenant сессии."""

    async def get_details(
        self, product_id: ProductIdVO, locale: ProductLocaleVO
    ) -> ProductDetailsDTO | None: ...
