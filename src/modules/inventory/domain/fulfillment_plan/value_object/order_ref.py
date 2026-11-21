from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.fulfillment_plan.error import (
    InvalidFulfillmentOrderRefError,
)


@dataclass(frozen=True, slots=True)
class FulfillmentOrderRefVO:
    """Сохраняет систему и непрозрачную ссылку заказа без зависимости от его агрегата или Shipment."""

    system: str
    reference: str

    def __post_init__(self) -> None:
        """Убирает крайние пробелы, сохраняя регистр и ведущие нули, и запрещает управляющие символы."""
        for name in ("system", "reference"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.strip()
                or any(category(char) in ("Cc", "Cf") for char in value)
            ):
                raise InvalidFulfillmentOrderRefError(
                    "Нужны непустые система и ссылка заказа без управляющих символов."
                )
            object.__setattr__(self, name, value.strip())
