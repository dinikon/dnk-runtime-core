from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, BinaryIO
from uuid import UUID


class CatalogImageStream(Protocol):
    """Поток потребителя Catalog без SDK и DB-сессии."""

    def __aiter__(self) -> AsyncIterator[bytes]:
        """Возвращает асинхронный поток порций."""
        ...

    async def aclose(self) -> None:
        """Закрывает ресурс при завершении или отмене ответа."""
        ...


@dataclass(frozen=True, slots=True)
class UploadedCatalogImageFile:
    """Проверенный файл изображения из контракта потребителя."""

    file_id: UUID
    name: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class CatalogImageFileContent:
    """Управляемый поток с безопасными метаданными файла."""

    file_id: UUID
    name: str
    content_type: str
    size_bytes: int
    stream: CatalogImageStream


class CatalogImageFilesPort(Protocol):
    """Проверяет и загружает готовые изображения текущего tenant."""

    async def upload(
        self,
        tenant_id: UUID,
        source: BinaryIO,
        size_bytes: int,
        name: str,
        content_type: str,
    ) -> UploadedCatalogImageFile:
        """Загружает изображение с проверкой реального формата и лимита размера."""
        ...

    async def ensure_images(self, tenant_id: UUID, file_ids: tuple[UUID, ...]) -> None:
        """Проверяет доступность и image MIME прикрепляемых файлов."""
        ...

    async def content(self, tenant_id: UUID, file_id: UUID) -> CatalogImageFileContent:
        """Открывает поток разрешённого tenant файла."""
        ...
