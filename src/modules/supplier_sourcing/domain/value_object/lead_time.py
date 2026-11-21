from dataclasses import dataclass
from datetime import timedelta

from src.modules.supplier_sourcing.domain.error import InvalidSupplierLeadTimeError


@dataclass(frozen=True, slots=True)
class SupplierLeadTimeVO:
    """Задаёт длительность поставки, включая немедленную поставку."""

    value: timedelta

    def __post_init__(self) -> None:
        """Отклоняет значения без единицы времени и отрицательную длительность."""
        if not isinstance(self.value, timedelta) or self.value < timedelta(0):
            raise InvalidSupplierLeadTimeError(
                "Срок поставки должен быть неотрицательной длительностью."
            )
