from decimal import Decimal

from src.modules.inventory.domain.error import InvalidQuantityError
from src.modules.inventory.domain.policy.stock_quantity import StockQuantityPolicy
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_rules import QuantityRulesVO
from src.modules.inventory.domain.value_object.stock_delta import StockDeltaVO


class QuantityArithmeticPolicy:
    """Складывает и вычитает физические величины точно, независимо от внешнего Decimal context."""

    @staticmethod
    def add(left: QuantityVO, right: QuantityVO) -> QuantityVO:
        """Возвращает точную сумму без изменения операндов и округления."""
        return QuantityArithmeticPolicy._apply(left, right, subtract=False)

    @staticmethod
    def subtract(left: QuantityVO, right: QuantityVO) -> QuantityVO:
        """Возвращает точную неотрицательную разность с общей защитой арифметики."""
        return QuantityArithmeticPolicy._apply(left, right, subtract=True)

    @staticmethod
    def _apply(left: QuantityVO, right: QuantityVO, *, subtract: bool) -> QuantityVO:
        """Выбирает технический общий шаг операндов, не подменяя правил конкретного товара."""
        if not isinstance(left, QuantityVO) or not isinstance(right, QuantityVO):
            raise InvalidQuantityError("Для арифметики нужны QuantityVO.")
        exponent = min(int(value.value.as_tuple().exponent) for value in (left, right))
        delta = right.value.copy_negate() if subtract else right.value
        return StockQuantityPolicy.apply_delta(
            quantity=left,
            delta=StockDeltaVO(delta),
            rules=QuantityRulesVO(Decimal((0, (1,), exponent))),
        )
