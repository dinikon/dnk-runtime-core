from dataclasses import dataclass
from unicodedata import category

from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
)


@dataclass(frozen=True, slots=True)
class ExternalWarehouseCodeVO:
    """Код склада в системе поставщика с сохранением регистра и ведущих нулей."""

    value: str

    def __post_init__(self) -> None:
        """Требует непустой внешний код без управляющих символов и обрезает пробелы."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidSupplierSourceValueError(
                "Укажите непустой внешний код без управляющих символов."
            )
        object.__setattr__(self, "value", self.value.strip())
