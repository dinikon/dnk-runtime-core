from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class FeedFileMissingError(Exception):
    """Активный файл больше недоступен в текущем tenant."""


class FeedFileStorageError(Exception):
    """Хранилище временно недоступно."""


class ExportContentStream(Protocol):
    """Читает и закрывает поток файла без зависимости от HTTP или Files."""

    def __aiter__(self) -> AsyncIterator[bytes]:
        """Читает файл ограниченными порциями."""
        ...

    async def aclose(self) -> None:
        """Освобождает поток."""
        ...


@dataclass(frozen=True, slots=True)
class ExportFileContentDTO:
    """Передаёт поток готового файла и его длину."""

    size_bytes: int
    stream: ExportContentStream


class FeedExportContentPort(Protocol):
    """Открывает активный объект Files в доверенном tenant."""

    async def open(self, tenant_id: UUID, file_id: UUID) -> ExportFileContentDTO:
        """Возвращает поток, независимый от DB-сессии."""
        ...
