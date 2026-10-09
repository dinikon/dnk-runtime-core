from dataclasses import dataclass

from src.modules.warehousing.domain.warehouse.error import InvalidWarehouseTypeError


@dataclass(frozen=True, slots=True)
class WarehouseTypeVO:
    """Строковый код назначения склада без фиксированного справочника типов."""

    value: str

    def __post_init__(self) -> None:
        """Проверяет непустой код типа длиной до 64 символов."""
        if not isinstance(self.value, str):
            raise InvalidWarehouseTypeError("Тип склада должен быть строкой.")
        value = self.value.strip()
        if not 1 <= len(value) <= 64 or "\x00" in value:
            raise InvalidWarehouseTypeError("Тип склада должен содержать 1–64 символа.")
        object.__setattr__(self, "value", value)
