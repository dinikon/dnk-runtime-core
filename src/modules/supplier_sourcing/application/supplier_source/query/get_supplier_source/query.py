from dataclasses import dataclass
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)


@dataclass(frozen=True, slots=True)
class GetSupplierSourceQuery:
    """Определяет карточку источника текущего tenant."""

    source_id: SupplierSourceIdVO
