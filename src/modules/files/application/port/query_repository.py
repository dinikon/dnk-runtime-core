from dataclasses import dataclass
from typing import Protocol
from uuid import UUID
from src.modules.files.application.port.storage import StorageLocation
from src.modules.files.application.storage_provider.query.list_providers.dto import (
    ProviderListItemDTO,
)
from src.modules.files.application.bucket.query.list_buckets.dto import (
    BucketListItemDTO,
)


@dataclass(frozen=True, slots=True)
class FileContentLocationDTO:
    """Проекция координат файла для открытия потока без восстановления агрегата."""

    location: StorageLocation
    key: str
    name: str
    content_type: str
    size_bytes: int


class StorageQueryRepositoryProtocol(Protocol):
    """Читает специализированные проекции на tenant-сессии."""

    async def providers(self) -> tuple[ProviderListItemDTO, ...]:
        """Возвращает подключения без секретов и адресов хранилища."""
        ...

    async def buckets(self, provider_id: UUID | None) -> tuple[BucketListItemDTO, ...]:
        """Возвращает контейнеры со статистикой зарегистрированных файлов."""
        ...

    async def content_location(
        self, tenant_id: UUID, file_id: UUID
    ) -> FileContentLocationDTO | None:
        """Возвращает готовый файл вместе с координатами его контейнера."""
        ...

    async def contains_key(self, bucket_id: UUID, key: str) -> bool:
        """Проверяет наличие ключа в реестре без загрузки всего реестра."""
        ...
