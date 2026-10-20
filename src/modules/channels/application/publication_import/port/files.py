from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, BinaryIO
from uuid import UUID


class PublicationImportImageStream(Protocol):
    """Ограничивает управляемый Files поток контрактом потребителя."""

    def __aiter__(self) -> AsyncIterator[bytes]:
        """Возвращает последовательность бинарных порций."""
        ...

    async def aclose(self) -> None:
        """Закрывает файловый ресурс после ответа или отмены."""
        ...


@dataclass(frozen=True, slots=True)
class PublicationImportImageContentDTO:
    """Передаёт проверенный поток изображения для приватного предпросмотра."""

    content_type: str
    size_bytes: int
    stream: PublicationImportImageStream


class PublicationImportFilesPort(Protocol):
    """Ограничивает файловые операции снимком, выбранным ядром."""

    async def upload(
        self, tenant_id: UUID, source: BinaryIO, size_bytes: int, content_type: str
    ) -> UUID:
        """Проверяет изображение и регистрирует его в текущем UoW."""
        ...

    async def release(
        self, tenant_id: UUID, actor_id: UUID, file_ids: tuple[UUID, ...]
    ) -> None:
        """Освобождает временные файлы, сохраняя используемые Catalog."""
        ...

    async def content(
        self, tenant_id: UUID, file_id: UUID
    ) -> PublicationImportImageContentDTO:
        """Читает только уже разрешённый приложением файл."""
        ...
