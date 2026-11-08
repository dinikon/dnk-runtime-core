from dataclasses import dataclass
from typing import ClassVar

from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentSourceError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_kind import (
    FulfillmentSourceKind,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierOfferIdVO,
    FulfillmentSupplierSourceIdVO,
)


@dataclass(frozen=True, slots=True)
class SupplierDropshipSourceRefVO:
    """Идентифицирует выбранное предложение и внешний источник прямой поставки."""

    kind: ClassVar[FulfillmentSourceKind] = FulfillmentSourceKind.SUPPLIER_DROPSHIP
    supplier_source_id: FulfillmentSupplierSourceIdVO
    supplier_offer_id: FulfillmentSupplierOfferIdVO

    def __post_init__(self) -> None:
        """Требует отдельные типизированные ссылки источника и предложения."""
        if not isinstance(
            self.supplier_source_id, FulfillmentSupplierSourceIdVO
        ) or not isinstance(self.supplier_offer_id, FulfillmentSupplierOfferIdVO):
            raise InvalidFulfillmentSourceError(
                "Прямая поставка требует идентификаторы источника и предложения."
            )
