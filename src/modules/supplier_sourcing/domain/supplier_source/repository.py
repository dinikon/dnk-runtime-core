from typing import Protocol
from src.modules.supplier_sourcing.domain.supplier_source.aggregate import (
    SupplierSource,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)


class SupplierSourceRepositoryProtocol(Protocol):
    """Хранит целый источник в общей tenant-транзакции."""

    async def add(self, source: SupplierSource) -> None:
        """Добавляет карточку и режимы без commit."""
        ...

    async def get_for_update(
        self, identifier: SupplierSourceIdVO
    ) -> SupplierSource | None:
        """Блокирует корень и восстанавливает его режимы."""
        ...

    async def save(self, source: SupplierSource) -> None:
        """Записывает существующий источник без изменения поставщика."""
        ...
