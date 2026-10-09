from typing import Protocol
from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)


class ProductRepositoryProtocol(Protocol):
    """Контракт хранения полного агрегата в сессии текущего tenant."""

    async def get(self, identifier: ProductIdVO) -> Product:
        """Восстанавливает агрегат либо сообщает об отсутствии."""
        ...

    async def add(self, entity: Product) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, entity: Product) -> None:
        """Сохраняет доменное состояние без commit."""
        ...

    async def delete(self, entity: Product) -> None:
        """Удаляет агрегат после доменных проверок без commit."""
        ...

    async def get_by_type(self, identifier: ProductTypeIdVO) -> tuple[Product, ...]:
        """Загружает агрегаты для проверки контента при изменении схемы."""
        ...
