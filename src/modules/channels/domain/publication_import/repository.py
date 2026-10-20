from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.publication_import.aggregate import (
    PublicationImportPreparation,
)


class PublicationImportRepositoryProtocol(Protocol):
    """Хранит самостоятельный процесс подготовки в общей tenant-транзакции."""

    async def get(
        self, identifier: EntityIdVO, *, lock: bool = True
    ) -> PublicationImportPreparation:
        """Возвращает процесс или предметную ошибку отсутствия."""
        ...

    async def add(self, preparation: PublicationImportPreparation) -> None:
        """Добавляет процесс без самостоятельного commit."""
        ...

    async def save(self, preparation: PublicationImportPreparation) -> None:
        """Сохраняет переход lifecycle без commit."""
        ...

    async def lock_request(self, tenant_id: EntityIdVO, identifier: EntityIdVO) -> None:
        """Сериализует идемпотентный запуск до появления строки."""
        ...
