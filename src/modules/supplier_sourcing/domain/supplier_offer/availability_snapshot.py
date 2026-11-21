from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from dataclasses import dataclass

from src.modules.supplier_sourcing.domain.supplier_offer.error import (
    InvalidSupplierOfferValueError,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.identifier import (
    SupplierOfferIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.uom_code import (
    SupplierOfferUomCodeVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)


@dataclass(frozen=True, slots=True)
class SupplierOfferAvailabilitySnapshot:
    """Передаёт принадлежность предложения, ограничение по источнику и базовую единицу."""

    id: SupplierOfferIdVO
    supplier: SupplierReferenceVO
    source_id: SupplierSourceIdVO | None
    base_uom: SupplierOfferUomCodeVO

    def ensure_valid(self) -> None:
        """Проверяет типизированные поля, необходимые для учёта наличия."""
        if (
            not isinstance(self.id, SupplierOfferIdVO)
            or not isinstance(self.supplier, SupplierReferenceVO)
            or (
                self.source_id is not None
                and not isinstance(self.source_id, SupplierSourceIdVO)
            )
            or not isinstance(self.base_uom, SupplierOfferUomCodeVO)
        ):
            raise InvalidSupplierOfferValueError(
                "Нужны идентификаторы и базовая единица предложения."
            )
