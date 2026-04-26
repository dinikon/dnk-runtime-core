from dataclasses import dataclass

from src.modules.inventory.domain.product.error import InvalidProductSkuError


@dataclass(slots=True, frozen=True)
class SkuVO:
    """Value object SKU товара."""

    value: str

    def __post_init__(self) -> None:
        """Нормализует и проверяет непустой SKU."""
        if not isinstance(self.value, str):
            raise InvalidProductSkuError()
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProductSkuError()
        object.__setattr__(self, "value", normalized)
