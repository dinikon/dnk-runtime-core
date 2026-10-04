from typing import Protocol

from src.modules.inventory.domain.sku.aggregate import Sku


class SkuRepositoryProtocol(Protocol):
    """Запись агрегата в текущем tenant и транзакции внешнего UoW."""

    async def add(self, sku: Sku) -> None:
        """Сохраняет SKU; занятый код вызывает SkuCodeAlreadyExistsError."""
        ...
