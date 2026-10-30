from typing import Protocol
from uuid import UUID

from src.modules.channels.application.content_media.contracts import (
    MediaFile,
    OpenMediaContent,
)


class MediaFilesPort(Protocol):
    """Разделяет SQL-описание файлов, блокировки и сетевое чтение."""

    async def describe(
        self, file_ids: tuple[UUID, ...], *, for_update: bool = False
    ) -> tuple[MediaFile, ...]:
        """Получает только готовые файлы своего tenant; сеть не открывает."""
        ...

    async def inspect(self, files: tuple[MediaFile, ...]) -> None:
        """Вне транзакции подтверждает наличие, ownership, размер и фактический MIME."""
        ...

    async def open(self, file: MediaFile) -> OpenMediaContent:
        """Открывает проверенный поток без SQL; caller закрывает его также при отмене."""
        ...
