from dataclasses import dataclass
from decimal import Decimal

from src.modules.catalog.domain.error import InvalidCatalogValueError


@dataclass(frozen=True, slots=True)
class PurchasePriceVO:
    """Самостоятельная закупочная стоимость продаваемой позиции."""

    value: Decimal

    def __post_init__(self) -> None:
        """Проверяет сумму без округления и сравнения с ценой продажи."""
        if (
            not isinstance(self.value, Decimal)
            or not self.value.is_finite()
            or self.value < 0
            or self.value.as_tuple().exponent < -6
        ):
            raise InvalidCatalogValueError(
                "Закупочная цена должна быть неотрицательной суммой с точностью до 6 знаков.",
                ("purchase_price",),
            )
