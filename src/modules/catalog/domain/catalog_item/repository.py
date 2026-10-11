from typing import Protocol
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class CatalogItemRepositoryProtocol(Protocol):
    """Хранит корни с принадлежащими дочерними CatalogItem, без независимого Variant CRUD."""

    async def get(self, identifier: CatalogItemIdVO) -> CatalogItem:
        """Загружает корень и его состав либо сообщает об отсутствии."""
        ...

    async def add(self, entity: CatalogItem) -> None:
        """Добавляет проверенный агрегат в общей транзакции."""
        ...

    async def save(self, entity: CatalogItem) -> None:
        """Сохраняет только изменённые записи без commit."""
        ...

    async def delete(self, entity: CatalogItem) -> None:
        """Удаляет корень после доменной проверки зависимостей."""
        ...
