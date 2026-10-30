from typing import Protocol
from uuid import UUID

from src.modules.channels.application.product_representation.contracts import (
    RepresentationBindingSource,
    RepresentationState,
)


class RepresentationQueryRepositoryProtocol(Protocol):
    """Читает только принадлежащую каналу группу в текущей tenant-схеме."""

    async def binding(
        self, *, channel_id: UUID, group_id: UUID
    ) -> RepresentationBindingSource | None:
        """Возвращает якоря и стабильные ID пар без raw и секретов подключения."""
        ...

    async def state(self, group_id: UUID) -> RepresentationState:
        """Возвращает сохранённое намерение или defaults без записи в БД."""
        ...
