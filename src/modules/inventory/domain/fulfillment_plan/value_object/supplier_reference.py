from dataclasses import dataclass
from enum import StrEnum
from typing import Self
from uuid import UUID
from src.modules.inventory.domain.fulfillment_plan.value_object.supplier_identity import (
    FulfillmentSupplierIdVO,
)
from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentPlanValueError,
)


class FulfillmentSupplierModelKey(StrEnum):
    """Ограничивает поставщика компанией или контактом CRM."""

    COMPANY = "crm.company"
    CONTACT = "crm.contact"


@dataclass(frozen=True, slots=True)
class FulfillmentSupplierReferenceVO:
    """Полная идентичность поставщика: тип контрагента и его номинальный UUID."""

    model_key: FulfillmentSupplierModelKey
    identifier: FulfillmentSupplierIdVO

    def __post_init__(self) -> None:
        """Отклоняет неполную ссылку и значения чужого контекста."""
        if not isinstance(
            self.model_key, FulfillmentSupplierModelKey
        ) or not isinstance(self.identifier, FulfillmentSupplierIdVO):
            raise InvalidFulfillmentPlanValueError(
                "Нужны тип контрагента и типизированный идентификатор поставщика."
            )

    @classmethod
    def from_value(cls, model_key: str, identifier: UUID) -> Self:
        """Преобразует публичную пару примитивов в локальную ссылку контекста."""
        try:
            kind = FulfillmentSupplierModelKey(model_key)
        except (ValueError, TypeError) as exc:
            raise InvalidFulfillmentPlanValueError(
                "Поставщик должен быть компанией или контактом CRM."
            ) from exc
        return cls(kind, FulfillmentSupplierIdVO.from_value(identifier))
