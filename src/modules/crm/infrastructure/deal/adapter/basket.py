from uuid import UUID
from src.modules.crm.application.basket.values import (
    BasketInput,
    OwnerBasketProjection,
    BasketSummaryProjection,
)
from src.modules.crm.application.basket.service.basket import BasketApplicationService


class DealBasketAdapter:
    """Фиксирует model_key, не раскрывая его пользовательскому API."""

    def __init__(self, service: BasketApplicationService) -> None:
        """Принимает общий прикладной сервис корзины."""
        self._service = service

    async def create(
        self, owner_id: UUID, tenant_id: UUID, values: BasketInput, locale: str
    ) -> tuple[UUID, dict[str, UUID]]:
        """Создаёт корзину данного владельца."""
        return await self._service.create(
            "crm.deal", owner_id, tenant_id, values, locale
        )

    async def replace(
        self, owner_id: UUID, tenant_id: UUID, values: BasketInput, locale: str
    ) -> dict[str, UUID]:
        """Заменяет корзину данного владельца."""
        return await self._service.replace(
            "crm.deal", owner_id, tenant_id, values, locale
        )

    async def get(self, owner_id: UUID) -> OwnerBasketProjection:
        """Читает корзину данного владельца."""
        return await self._service.get("crm.deal", owner_id)

    async def summaries(
        self, owner_ids: tuple[UUID, ...]
    ) -> dict[UUID, BasketSummaryProjection]:
        """Читает сводки данного типа владельцев."""
        return await self._service.summaries("crm.deal", owner_ids)
