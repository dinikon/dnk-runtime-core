from typing import Protocol
from uuid import UUID
from src.modules.crm.application.basket.values import (
    OwnerBasketProjection,
    BasketSummaryProjection,
)


class BasketQueryRepositoryProtocol(Protocol):
    """Проекции только внутри ответственности Basket."""

    async def get_owner(
        self, model_key: str, owner_id: UUID
    ) -> OwnerBasketProjection | None:
        """Читает согласованный снимок заголовка и строк."""
        ...

    async def summaries(
        self, model_key: str, owner_ids: tuple[UUID, ...]
    ) -> dict[UUID, BasketSummaryProjection]:
        """Читает одну пакетную проекцию итогов."""
        ...
