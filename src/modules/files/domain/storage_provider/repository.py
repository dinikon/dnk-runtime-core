from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.storage_provider.aggregate import StorageProvider


class StorageProviderRepositoryProtocol(Protocol):
    """Контракт хранения агрегатов в уже выбранной tenant-схеме."""

    async def get(self, identifier: EntityIdVO) -> StorageProvider:
        """Загружает агрегат либо сообщает об отсутствии."""
        ...

    async def add(self, aggregate: StorageProvider) -> None:
        """Добавляет агрегат без самостоятельного commit."""
        ...

    async def save(self, aggregate: StorageProvider) -> None:
        """Сохраняет состояние без самостоятельного commit."""
        ...

    async def get_system(
        self, *, for_registration: bool = False
    ) -> StorageProvider | None:
        """Находит системное подключение в текущей tenant-сессии."""
        ...
