from typing import Protocol
from uuid import UUID


class CompanyStockOwnerUsagePort(Protocol):
    """Проверяет внешние ссылки на компанию как владельца запаса."""

    async def is_used(self, identifier: UUID) -> bool:
        """Читает факт использования через публичную границу Inventory."""
        ...
