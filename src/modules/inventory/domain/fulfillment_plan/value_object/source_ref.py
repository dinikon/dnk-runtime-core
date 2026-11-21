from dataclasses import dataclass

from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentSourceError,
)
from src.modules.inventory.domain.fulfillment_plan.value_object.source_kind import (
    FulfillmentSourceKind,
)
from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO


@dataclass(frozen=True, slots=True)
class FulfillmentSourceRefVO:
    """Идентифицирует выбранный собственный склад без хранения чужого агрегата или будущих полей поставщика."""

    kind: FulfillmentSourceKind
    warehouse_id: WarehouseIdVO

    def __post_init__(self) -> None:
        """Требует реализованный вид OWN_WAREHOUSE и типизированный ID склада."""
        if self.kind is not FulfillmentSourceKind.OWN_WAREHOUSE or not isinstance(
            self.warehouse_id, WarehouseIdVO
        ):
            raise InvalidFulfillmentSourceError(
                "Поддерживается только OWN_WAREHOUSE с WarehouseIdVO."
            )
