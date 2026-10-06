from typing import Protocol

from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)


class ProductTypeRepositoryProtocol(Protocol):
    """Хранение корня ProductType в текущей tenant-транзакции."""

    async def add(self, product_type: ProductType) -> None: ...

    async def get_for_update(self, type_id: ProductTypeIdVO) -> ProductType | None: ...

    async def save(self, product_type: ProductType) -> None: ...

    async def delete(self, product_type: ProductType) -> None: ...
