from typing import Protocol
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class CatalogItemRepositoryProtocol(Protocol):
    """Хранит самостоятельные товары в общей tenant-транзакции."""

    async def get(self, identifier: CatalogItemIdVO) -> CatalogItem:
        """Загружает товар либо сообщает об отсутствии."""
        ...

    async def add(self, entity: CatalogItem) -> None:
        """Добавляет проверенный агрегат в общей транзакции."""
        ...

    async def save(self, entity: CatalogItem) -> None:
        """Сохраняет только изменённые записи без commit."""
        ...

    async def delete(self, entity: CatalogItem) -> None:
        """Удаляет товар после доменной проверки зависимостей."""
        ...
