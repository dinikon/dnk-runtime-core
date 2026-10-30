from typing import Protocol
from uuid import UUID

from src.modules.channels.application.content_media.contracts import MediaReadRow


class ContentMediaQueryRepositoryProtocol(Protocol):
    """Читает media и собственные ссылки Channels без чужого SQL."""

    async def get(self, identifier: UUID) -> MediaReadRow | None:
        """Возвращает media вместе с ID владельца подключения."""
        ...

    async def groups(self, connection_id: UUID) -> tuple[UUID, ...]:
        """Возвращает группы с сохранённым разрешением экспорта."""
        ...

    async def used_images(self, file_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        """Учитывает все сохранённые overrides и незавершённые передачи."""
        ...
