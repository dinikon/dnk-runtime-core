from typing import Protocol
from uuid import UUID


class ContentDeliveryAuthorizationPort(Protocol):
    """Проверяет права сохранённого инициатора без HTTP-сессии."""

    async def require(
        self, *, actor_id: UUID, channel_id: UUID, file_ids: tuple[UUID, ...]
    ) -> None:
        """Проверяет управление каналом и чтение каждого фактически выбранного файла."""
        ...
