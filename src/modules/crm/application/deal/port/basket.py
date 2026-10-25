from typing import Protocol
from uuid import UUID
from src.modules.crm.application.basket.values import (
    BasketInput,
    OwnerBasketProjection,
    BasketSummaryProjection,
)


class DealBasketPort(Protocol):
    """Контракт корзины проверенного владельца Deal."""

    async def create(
        self, owner_id: UUID, tenant_id: UUID, values: BasketInput, locale: str
    ) -> tuple[UUID, dict[str, UUID]]:
        """Создаёт корзину уже проверенного владельца."""
        ...

    async def replace(
        self, owner_id: UUID, tenant_id: UUID, values: BasketInput, locale: str
    ) -> dict[str, UUID]:
        """Заменяет состав с проверкой revision."""
        ...

    async def get(self, owner_id: UUID) -> OwnerBasketProjection:
        """Читает согласованную проекцию без скрытых записей."""
        ...

    async def summaries(
        self, owner_ids: tuple[UUID, ...]
    ) -> dict[UUID, BasketSummaryProjection]:
        """Возвращает пакетные сводки для страницы владельцев."""
        ...
