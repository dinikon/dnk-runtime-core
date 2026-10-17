from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class CatalogMutationLockPort(Protocol):
    """Согласованный порядок справочного guard и блокировок независимых товаров."""

    async def acquire(self, tenant_id: EntityIdVO) -> None:
        """Получает exclusive reference guard для мутации справочников."""
        ...

    async def acquire_read(self, tenant_id: EntityIdVO) -> None:
        """Обычная read projection не требует advisory lock."""
        ...

    async def acquire_reference(self, tenant_id: EntityIdVO) -> None:
        """Получает shared reference guard перед изменением товара."""
        ...

    async def acquire_item(
        self, tenant_id: EntityIdVO, item_id: CatalogItemIdVO
    ) -> None:
        """Сериализует записи только одного товара до конца UoW."""
        ...
