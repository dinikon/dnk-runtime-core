from typing import Protocol
from uuid import UUID
from src.modules.channels.application.content_update.query.get_content_update.dto import (
    GetContentUpdateResultDTO,
)
from src.modules.channels.application.content_update.query.list_content_updates.dto import (
    ListContentUpdatesResultDTO,
)


class ContentUpdateQueries(Protocol):
    """Читает собственные проекции операций без восстановления агрегатов."""

    async def scope(self, identifier: UUID) -> tuple[UUID, UUID]:
        """Возвращает канал и автора для устойчивого порядка блокировок."""
        ...

    async def get(self, identifier: UUID, actor_id: UUID) -> GetContentUpdateResultDTO:
        """Читает детали только операции текущего автора."""
        ...

    async def recent(
        self, channel_id: UUID, actor_id: UUID
    ) -> ListContentUpdatesResultDTO:
        """Возвращает ограниченную историю операций канала."""
        ...
