from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogMutationLockPort(Protocol):
    """Сериализация записей Catalog до завершения внешнего tenant UoW."""

    async def acquire(self, tenant_id: EntityIdVO) -> None:
        """Получает блокировку общего порядка изменений схем и содержимого."""
        ...

    async def acquire_read(self, tenant_id: EntityIdVO) -> None:
        """Защищает согласованное чтение табличных частей от конкурентной записи."""
        ...
