from dataclasses import dataclass

from src.modules.warehousing.domain.warehouse.error import InvalidWarehouseTimezoneError


@dataclass(frozen=True, slots=True)
class WarehousePolicyVO:
    """Настройки склада: код IANA timezone, проверяемый через внешний порт."""

    timezone: str

    def __post_init__(self) -> None:
        """Проверяет собственное значение без обращения к справочнику или I/O."""
        if not isinstance(self.timezone, str):
            raise InvalidWarehouseTimezoneError("Часовой пояс должен быть строкой.")
        value = self.timezone.strip()
        if not 1 <= len(value) <= 128 or "\x00" in value:
            raise InvalidWarehouseTimezoneError(
                "Часовой пояс должен содержать 1–128 символов."
            )
        object.__setattr__(self, "timezone", value)
