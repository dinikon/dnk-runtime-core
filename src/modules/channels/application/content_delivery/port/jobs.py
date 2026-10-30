from datetime import datetime
from typing import Protocol
from uuid import UUID
from src.modules.channels.domain.content_delivery.aggregate import ContentDelivery


class ContentDeliveryJobsPort(Protocol):
    """Использует надёжную постановку и lease существующих Shared Jobs."""

    async def schedule(
        self, *, tenant_id: UUID, delivery: ContentDelivery, now: datetime
    ) -> None:
        """Сохраняет только идентификаторы в той же транзакции, что агрегат."""
        ...

    async def owns(
        self,
        *,
        tenant_id: UUID,
        job_id: UUID,
        lock_token: str,
        for_update: bool = False,
    ) -> bool:
        """Проверяет действующий lease перед подготовкой и фиксацией результата."""
        ...

    async def active(self, *, tenant_id: UUID, job_id: UUID) -> bool:
        """Определяет утраченное или окончательно завершённое задание."""
        ...

    async def cancel_channel(
        self, *, tenant_id: UUID, channel_id: UUID, now: datetime
    ) -> None:
        """Отменяет работу удалённого подключения в общей транзакции."""
        ...
