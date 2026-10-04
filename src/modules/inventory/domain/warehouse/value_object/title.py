from dataclasses import dataclass

from src.modules.inventory.domain.warehouse.error import InvalidWarehouseTitleError


@dataclass(frozen=True, slots=True)
class WarehouseTitleVO:
    """Нормализованное название склада длиной от 1 до 255 символов."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidWarehouseTitleError("Warehouse title must be a string.")
        value = self.value.strip()
        if not 1 <= len(value) <= 255:
            raise InvalidWarehouseTitleError(
                "Warehouse title must contain 1 to 255 characters."
            )
        object.__setattr__(self, "value", value)
