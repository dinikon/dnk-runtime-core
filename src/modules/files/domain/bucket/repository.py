from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.bucket.aggregate import Bucket


class BucketRepositoryProtocol(Protocol):
    """Контракт хранения агрегатов в уже выбранной tenant-схеме."""

    async def get(self, identifier: EntityIdVO) -> Bucket:
        """Загружает агрегат либо сообщает об отсутствии."""
        ...

    async def add(self, aggregate: Bucket) -> None:
        """Добавляет агрегат без самостоятельного commit."""
        ...

    async def save(self, aggregate: Bucket) -> None:
        """Сохраняет состояние без самостоятельного commit."""
        ...

    async def get_system(self, provider_id: EntityIdVO) -> Bucket | None:
        """Находит единственный системный бакет подключения."""
        ...

    async def list_all(self) -> tuple[Bucket, ...]:
        """Загружает контейнеры для процесса физической очистки."""
        ...
