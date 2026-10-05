from typing import Protocol

from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO


class ProductRepositoryProtocol(Protocol):
    """Запись Product в сессии текущего tenant."""

    async def add(self, product: Product) -> None: ...

    async def get_for_update(self, product_id: ProductIdVO) -> Product | None: ...

    async def save_content(self, product: Product, locale: ProductLocaleVO) -> None: ...
