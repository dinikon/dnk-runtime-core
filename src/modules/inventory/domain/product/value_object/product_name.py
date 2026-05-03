from dataclasses import dataclass

from src.modules.inventory.domain.product.error import InvalidProductNameError


@dataclass(slots=True, frozen=True)
class ProductNameVO:
    """Value object названия товара."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует и проверяет непустое название товара."""
        if not isinstance(self.value, str):
            raise InvalidProductNameError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProductNameError()
        object.__setattr__(self, "value", normalized)
