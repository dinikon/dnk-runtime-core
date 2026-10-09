from dataclasses import dataclass

from src.modules.warehousing.domain.warehouse.error import InvalidWarehouseCodeError


@dataclass(frozen=True, slots=True)
class WarehouseCodeVO:
    """Нормализованный код склада, сравниваемый без учёта регистра."""

    value: str

    def __post_init__(self) -> None:
        """Удаляет крайние пробелы, переводит код в верхний регистр и проверяет длину."""
        if not isinstance(self.value, str):
            raise InvalidWarehouseCodeError("Код склада должен быть строкой.")
        value = self.value.strip().upper()
        if not 1 <= len(value) <= 64 or "\x00" in value:
            raise InvalidWarehouseCodeError("Код склада должен содержать 1–64 символа.")
        object.__setattr__(self, "value", value)
