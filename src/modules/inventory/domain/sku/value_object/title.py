from dataclasses import dataclass

from src.modules.inventory.domain.sku.error import InvalidSkuTitleError


@dataclass(frozen=True, slots=True)
class SkuTitleVO:
    """Учётное название SKU, независимое от контента товарной карточки."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise InvalidSkuTitleError("title: ожидается строка.")
        value = self.value.strip()
        if not 1 <= len(value) <= 255:
            raise InvalidSkuTitleError("title: требуется от 1 до 255 символов.")
        object.__setattr__(self, "value", value)
