from dataclasses import dataclass

from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.domain.value_object.supplier_id import SupplierIdVO


@dataclass(frozen=True, slots=True)
class SupplierSourceIdentitySnapshot:
    """Передаёт идентичность источника и его принадлежность поставщику."""

    id: SupplierSourceIdVO
    supplier_id: SupplierIdVO

    def ensure_valid(self) -> None:
        """Требует отдельные типизированные идентификаторы источника и поставщика."""
        if not isinstance(self.id, SupplierSourceIdVO) or not isinstance(
            self.supplier_id, SupplierIdVO
        ):
            raise InvalidSupplierSourceValueError(
                "Нужны идентификаторы источника и его поставщика."
            )
