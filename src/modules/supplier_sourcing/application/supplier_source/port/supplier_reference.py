from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SupplierReference:
    """Публичное имя поставщика с полной локальной идентичностью."""

    supplier: SupplierReferenceVO
    name: str


class SupplierReferencePort(Protocol):
    """Проверяет компанию либо контакт в текущем tenant."""

    async def get(
        self, supplier: SupplierReferenceVO, *, lock: bool = False
    ) -> SupplierReference | None:
        """Проверяет точную пару; lock удерживает запись CRM до конца UoW."""
        ...

    async def get_many(
        self, suppliers: tuple[SupplierReferenceVO, ...]
    ) -> dict[SupplierReferenceVO, SupplierReference]:
        """Возвращает имена пакетом с составными ключами результата."""
        ...
