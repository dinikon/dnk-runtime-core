from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.shipment.error import InvalidShipmentOrderRefError


@dataclass(frozen=True, slots=True)
class ShipmentOrderRefVO:
    """Сохраняет систему и ссылку одного исходного заказа без владения чужим агрегатом."""

    system: str
    reference: str

    def __post_init__(self) -> None:
        """Требует непустые строки без управляющих символов, сохраняя регистр и ведущие нули."""
        for name in ("system", "reference"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value.strip()
                or any(category(char) in ("Cc", "Cf") for char in value)
            ):
                raise InvalidShipmentOrderRefError(
                    "Укажите систему и ссылку заказа без управляющих символов."
                )
            object.__setattr__(self, name, value.strip())
