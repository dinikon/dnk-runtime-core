from dataclasses import dataclass

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
)
from src.modules.external_fulfillment.domain.value_object.references import (
    ExternalFulfillmentPlanIdVO,
)


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentPlanRefVO:
    """Фиксирует план и версию, из которой собран внешний заказ."""

    plan_id: ExternalFulfillmentPlanIdVO
    plan_version: int

    def __post_init__(self) -> None:
        """Требует номинальный ID и строгую целую версию от нуля."""
        if (
            not isinstance(self.plan_id, ExternalFulfillmentPlanIdVO)
            or type(self.plan_version) is not int
            or self.plan_version < 0
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужны идентификатор плана и неотрицательная целая версия."
            )
