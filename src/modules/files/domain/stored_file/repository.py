from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.files.domain.stored_file.aggregate import StoredFile


class StoredFileRepositoryProtocol(Protocol):
    """Контракт хранения агрегатов в уже выбранной tenant-схеме."""

    async def get(self, identifier: EntityIdVO) -> StoredFile:
        """Загружает агрегат либо сообщает об отсутствии."""
        ...

    async def add(self, aggregate: StoredFile) -> None:
        """Добавляет агрегат без самостоятельного commit."""
        ...

    async def save(self, aggregate: StoredFile) -> None:
        """Сохраняет состояние без самостоятельного commit."""
        ...
