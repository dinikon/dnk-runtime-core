from typing import Protocol

from src.modules.inventory.domain.packaging_type.aggregate import PackagingType
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)


class PackagingTypeRepositoryProtocol(Protocol):
    """Определяет запись самостоятельного типа тары в общей tenant-транзакции."""

    async def get_for_update(
        self, identifier: PackagingTypeIdVO
    ) -> PackagingType | None:
        """Блокирует и восстанавливает актуальный агрегат либо возвращает None."""
        ...

    async def add(self, packaging_type: PackagingType) -> None:
        """Добавляет новый агрегат без самостоятельного commit."""
        ...

    async def save(self, packaging_type: PackagingType) -> None:
        """Обновляет существующий агрегат по ID без upsert и самостоятельного commit."""
        ...
