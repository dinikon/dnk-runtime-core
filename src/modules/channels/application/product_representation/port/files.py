from typing import Protocol
from uuid import UUID


class RepresentationFilesPort(Protocol):
    """Проверяет готовые изображения tenant без открытия storage stream."""

    async def unavailable(
        self, file_ids: tuple[UUID, ...], *, for_update: bool = False
    ) -> tuple[UUID, ...]:
        """Возвращает недоступные ID, при записи удерживая Files locks до commit."""
        ...
