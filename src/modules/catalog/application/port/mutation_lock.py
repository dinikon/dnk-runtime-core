from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class CatalogMutationLockPort(Protocol):
    """Транзакционные блокировки независимых товаров."""

    async def acquire_item(
        self, tenant_id: EntityIdVO, item_id: CatalogItemIdVO
    ) -> None:
        """Сериализует записи только одного товара до конца UoW."""
        ...
