from typing import Protocol
from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)


class ProductTypeRepositoryProtocol(Protocol):
    """Контракт хранения полного агрегата в сессии текущего tenant."""

    async def get(self, identifier: ProductTypeIdVO) -> ProductType:
        """Восстанавливает агрегат либо сообщает об отсутствии."""
        ...

    async def add(self, entity: ProductType) -> None:
        """Добавляет агрегат без commit."""
        ...

    async def save(self, entity: ProductType) -> None:
        """Сохраняет доменное состояние без commit."""
        ...

    async def delete(self, entity: ProductType) -> None:
        """Удаляет агрегат после доменных проверок без commit."""
        ...

    async def is_used(self, identifier: ProductTypeIdVO) -> bool:
        """Проверяет ссылки для защищённого доменного изменения."""
        ...

    async def get_default_id(self) -> ProductTypeIdVO:
        """Возвращает системный тип, созданный tenant-миграцией."""
        ...
