from __future__ import annotations

from dataclasses import dataclass
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money_error import InvalidMoneyError
from src.modules.shared.domain.value_object.money_error import (
    MoneyCurrencyMismatchError,
)


@dataclass(frozen=True, slots=True)
class MoneyVO:
    """Неизменяемая знаковая сумма с валютой в точности NUMERIC(19,4)."""

    amount: Decimal
    currency: CurrencyVO

    def __post_init__(self) -> None:
        """Проверяет диапазон и округляет сумму независимо от ambient Decimal context."""
        if not isinstance(self.currency, CurrencyVO):
            raise InvalidMoneyError("Money currency must be CurrencyVO.")
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise InvalidMoneyError("Money amount must be a finite Decimal.")
        limit = Decimal("1000000000000000")
        if self.amount.copy_abs() >= limit:
            raise InvalidMoneyError("Money amount is outside NUMERIC(19,4) range.")
        try:
            with localcontext(Context(prec=40, rounding=ROUND_HALF_UP)):
                amount = self.amount.quantize(Decimal("0.0001"))
        except InvalidOperation as exc:
            raise InvalidMoneyError("Money amount cannot be rounded.") from exc
        if amount.copy_abs() >= limit:
            raise InvalidMoneyError("Rounded money amount exceeds NUMERIC(19,4).")
        if amount.is_zero():
            amount = amount.copy_abs()
        object.__setattr__(self, "amount", amount)

    def __add__(self, other: MoneyVO) -> MoneyVO:
        """Возвращает сумму денег одной валюты с проверкой диапазона результата."""
        self._ensure_same_currency(other)
        with localcontext(Context(prec=40, rounding=ROUND_HALF_UP)):
            return MoneyVO(self.amount + other.amount, self.currency)

    def __sub__(self, other: MoneyVO) -> MoneyVO:
        """Возвращает разность денег одной валюты, допуская отрицательный результат."""
        self._ensure_same_currency(other)
        with localcontext(Context(prec=40, rounding=ROUND_HALF_UP)):
            return MoneyVO(self.amount - other.amount, self.currency)

    def _ensure_same_currency(self, other: MoneyVO) -> None:
        """Отклоняет операнды вне денежного контракта или с другой валютой."""
        if not isinstance(other, MoneyVO):
            raise InvalidMoneyError("Money operand must be MoneyVO.")
        if self.currency != other.currency:
            raise MoneyCurrencyMismatchError("Money currencies must match.")
