from typing import Protocol

from src.modules.inventory.domain.product.entity import ProductEntity
from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.shared import EntityIdVO


class ProductCommandRepositoryProtocol(Protocol):
    """Порт командного хранения товаров."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        product_id: ProductIdVO,
    ) -> ProductEntity | None:
        """Загружает товар tenant по id или возвращает None."""
        ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        product: ProductEntity,
    ) -> ProductEntity:
        """Сохраняет товар tenant и возвращает актуальную entity."""
        ...

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        product_id: ProductIdVO,
    ) -> None:
        """Удаляет товар tenant по id."""
        ...
