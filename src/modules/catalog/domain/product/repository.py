from typing import Protocol

from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO


class ProductRepositoryProtocol(Protocol):
    """Запись Product в сессии текущего tenant."""

    async def add(self, product: Product) -> None: ...

    async def get_for_update(self, product_id: ProductIdVO) -> Product | None: ...

    async def save_content(self, product: Product, locale: ProductLocaleVO) -> None: ...

    async def save_categories(self, product: Product) -> None: ...

    async def save_variants(self, product: Product) -> None: ...

    async def save_variant_content(
        self, product: Product, variant_id: VariantIdVO, locale: ProductLocaleVO
    ) -> None: ...

    async def delete(self, product: Product) -> None: ...
