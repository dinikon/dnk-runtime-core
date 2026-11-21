from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from dataclasses import dataclass

from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)


@dataclass(frozen=True, slots=True)
class SupplierSourceIdentitySnapshot:
    """Передаёт идентичность источника и его принадлежность поставщику."""

    id: SupplierSourceIdVO
    supplier: SupplierReferenceVO

    def ensure_valid(self) -> None:
        """Требует отдельные типизированные идентификаторы источника и поставщика."""
        if not isinstance(self.id, SupplierSourceIdVO) or not isinstance(
            self.supplier, SupplierReferenceVO
        ):
            raise InvalidSupplierSourceValueError(
                "Нужны идентификаторы источника и его поставщика."
            )
