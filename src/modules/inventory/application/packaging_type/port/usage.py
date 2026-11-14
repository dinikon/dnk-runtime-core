from typing import Protocol

from src.modules.inventory.domain.packaging_type.deletion_usage import (
    PackagingTypeDeletionUsage,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)


class PackagingTypeUsagePort(Protocol):
    """Определяет чтение использования типа в общей tenant-транзакции без ORM-типов."""

    async def get(self, identifier: PackagingTypeIdVO) -> PackagingTypeDeletionUsage:
        """Возвращает факт любой сохранённой ссылки из ItemPackaging текущего tenant."""
        ...
