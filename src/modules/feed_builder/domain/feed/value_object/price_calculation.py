from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.feed_builder.domain.feed.entity.conditional_price_rule import (
    ConditionalPriceRule,
)
from src.modules.feed_builder.domain.feed.value_object.purchase_price_source import (
    PurchasePriceSourceVO,
)
from src.modules.feed_builder.domain.feed.validation import is_expression, sequence
from src.modules.feed_builder.domain.feed.limits import MAX_RULES
from src.modules.feed_builder.domain.feed.error import (
    InvalidPriceCalculationDefinitionError,
)

if TYPE_CHECKING:
    from src.modules.feed_builder.domain.feed.types import Expression


@dataclass(frozen=True, slots=True)
class PriceCalculationVO:
    """Хранит условные определения цены одного поля и обязательную формулу ELSE."""

    calculation_currency: CurrencyVO
    default_expression: Expression
    rules: tuple[ConditionalPriceRule, ...] = ()
    purchase_source: PurchasePriceSourceVO | None = None

    def __post_init__(self) -> None:
        """Замораживает состав и проверяет собственные типы без инвариантов Entity."""
        rules = sequence(self.rules, label="Price rules", maximum=MAX_RULES)
        if (
            not isinstance(self.calculation_currency, CurrencyVO)
            or not is_expression(self.default_expression)
            or not all(isinstance(value, ConditionalPriceRule) for value in rules)
        ):
            raise InvalidPriceCalculationDefinitionError(
                "Нужны валюта, выражение ELSE и типизированные правила."
            )
        if self.purchase_source is not None and not isinstance(
            self.purchase_source, PurchasePriceSourceVO
        ):
            raise InvalidPriceCalculationDefinitionError(
                "Нужен типизированный закупочный источник."
            )
        object.__setattr__(self, "rules", rules)
