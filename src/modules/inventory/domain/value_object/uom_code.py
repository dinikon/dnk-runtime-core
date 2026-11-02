from dataclasses import dataclass
from unicodedata import category

from src.modules.inventory.domain.error import InvalidUomCodeError


@dataclass(frozen=True, slots=True)
class UomCodeVO:
    """Код единицы учёта с сохранением регистра после trim."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет непустой код и запрещает управляющие символы."""
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or any(category(char) in ("Cc", "Cf") for char in self.value)
        ):
            raise InvalidUomCodeError("Укажите непустой код единицы учёта.")
        object.__setattr__(self, "value", self.value.strip())
