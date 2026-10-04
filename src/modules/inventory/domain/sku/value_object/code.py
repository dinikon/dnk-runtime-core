from dataclasses import dataclass

from src.modules.inventory.domain.sku.error import InvalidSkuCodeError


@dataclass(frozen=True, slots=True)
class SkuCodeVO:
    """Код SKU без пробелов по краям; регистр и внутренние пробелы сохраняются."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidSkuCodeError("code: ожидается строка.")
        value = self.value.strip()
        if not 1 <= len(value) <= 128 or any(
            ord(char) < 32 or ord(char) == 127 for char in value
        ):
            raise InvalidSkuCodeError(
                "code: требуется от 1 до 128 символов без управляющих символов."
            )
        object.__setattr__(self, "value", value)
