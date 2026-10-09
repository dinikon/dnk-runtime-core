from dataclasses import dataclass

from src.modules.warehousing.domain.warehouse.error import InvalidWarehouseTitleError


@dataclass(frozen=True, slots=True)
class WarehouseTitleVO:
    """Непустое название склада без крайних пробелов."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет тип и длину названия после удаления крайних пробелов."""
        if not isinstance(self.value, str):
            raise InvalidWarehouseTitleError("Название склада должно быть строкой.")
        value = self.value.strip()
        if not 1 <= len(value) <= 255 or "\x00" in value:
            raise InvalidWarehouseTitleError(
                "Название склада должно содержать 1–255 символов."
            )
        object.__setattr__(self, "value", value)
