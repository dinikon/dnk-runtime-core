"""Управляемое owned-хранилище для проверки SQL/HTTP без обращения к рабочим файлам."""

import base64
from collections.abc import Callable
from contextvars import ContextVar
from uuid import UUID

from src.modules.files.application.port.storage import (
    FileContentStream,
    StorageLocation,
    StorageOwnershipError,
)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a0ioAAAAASUVORK5CYII="
)


class MemoryImageStream:
    """Выдаёт небольшие порции и позволяет проверить закрытие каждого потока."""

    def __init__(self, data: bytes) -> None:
        """Сохраняет независимое состояние чтения."""
        self.data, self.offset, self.closed = data, 0, False

    def __aiter__(self) -> "MemoryImageStream":
        """Возвращает async iterator."""
        return self

    async def __anext__(self) -> bytes:
        """Позволяет проверить сборку raster-префикса из нескольких порций."""
        if self.closed or self.offset == len(self.data):
            raise StopAsyncIteration
        chunk = self.data[self.offset : self.offset + 7]
        self.offset += len(chunk)
        return chunk

    async def aclose(self) -> None:
        """Фиксирует освобождение ресурса."""
        self.closed = True


class MemoryImageStorage:
    """Проверяет ownership по tenant и выполняет заданный барьер перед чтением."""

    def __init__(self) -> None:
        """Создаёт пустой реестр и журнал потоков."""
        self.objects: dict[tuple[UUID, str], bytes] = {}
        self.streams: list[MemoryImageStream] = []
        self._before_open: ContextVar[Callable[[], None] | None] = ContextVar(
            "media_storage_probe", default=None
        )

    @property
    def before_open(self) -> Callable[[], None] | None:
        """Изолирует probe одной HTTP-задачи от конкурентной подготовки."""
        return self._before_open.get()

    @before_open.setter
    def before_open(self, value: Callable[[], None] | None) -> None:
        """Устанавливает проверку только для текущего async-контекста."""
        self._before_open.set(value)

    def resolve(self, location: StorageLocation) -> "MemoryImageStorage":
        """Выступает одновременно тестовым resolver и adapter."""
        return self

    async def open(self, location: StorageLocation, key: str) -> FileContentStream:
        """Не раскрывает отсутствующий или чужой ключ."""
        if self.before_open:
            self.before_open()
        try:
            data = self.objects[(location.tenant_id, key)]
        except KeyError:
            raise StorageOwnershipError() from None
        stream = MemoryImageStream(data)
        self.streams.append(stream)
        return stream

    async def exists_owned(self, location: StorageLocation, key: str) -> bool:
        """Проверяет ту же tenant-границу, что owned storage владельца."""
        if self.before_open:
            self.before_open()
        return (location.tenant_id, key) in self.objects
