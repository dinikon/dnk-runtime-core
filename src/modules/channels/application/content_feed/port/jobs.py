from datetime import datetime
from typing import Protocol
from uuid import UUID


class FeedImportJobsPort(Protocol):
    """Использует Shared Jobs для коротких этапов и проверок lease."""

    async def schedule(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        feed_id: UUID,
        operation_id: UUID,
        job_id: UUID,
        run_at: datetime,
    ) -> None:
        """Сохраняет только идентификаторы в общей транзакции с ContentFeed."""
        ...

    async def owns(self, *, tenant_id: UUID, job_id: UUID, lock_token: str) -> bool:
        """Проверяет токен и неистёкшую lease с блокировкой на момент commit."""
        ...

    async def active(self, *, tenant_id: UUID, job_id: UUID) -> bool:
        """Отличает активную работу от утраченной или окончательно завершённой."""
        ...

    async def cancel_channel(
        self, *, tenant_id: UUID, channel_id: UUID, now: datetime
    ) -> None:
        """Отзывает оставшиеся задания удаляемого канала в той же транзакции."""
        ...
