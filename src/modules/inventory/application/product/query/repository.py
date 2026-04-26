from typing import Protocol

from src.modules.inventory.application.product.dto import ProductDTO
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.inventory.domain.product.value_object import ProductIdVO
from src.modules.shared import EntityIdVO


class ProductQueryRepositoryProtocol(Protocol):
    """Порт чтения товаров для inventory query use cases."""

    async def get_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        product_id: ProductIdVO,
    ) -> ProductDTO | None:
        """Возвращает товар tenant по id или None."""
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
        category_id: CategoryIdVO | None = None,
    ) -> list[ProductDTO]:
        """Возвращает страницу товаров tenant."""
        ...


__all__ = ["ProductQueryRepositoryProtocol"]
