from dataclasses import dataclass
from typing import ClassVar
from src.modules.feed_builder.domain.feed.enum.value_definition_kind import (
    ValueDefinitionKind,
)
from src.modules.feed_builder.domain.feed.enum.money_value_mode import MoneyValueMode
from src.modules.feed_builder.domain.feed.value_object.source_reference import (
    SourceReferenceVO,
)
from src.modules.feed_builder.domain.feed.expression.value_object.price_calculation import (
    PriceCalculationVO,
)
from src.modules.feed_builder.domain.feed.error import InvalidFeedValueError


@dataclass(frozen=True, slots=True)
class MoneyValueDefinitionVO:
    """Задаёт ровно один способ получения числовой суммы без валютных преобразований."""

    kind: ClassVar[ValueDefinitionKind] = ValueDefinitionKind.MONEY
    mode: MoneyValueMode
    source: SourceReferenceVO | None = None
    calculation: PriceCalculationVO | None = None

    def __post_init__(self) -> None:
        """Запрещает смешанные режимы и неактивные source/calculation."""
        if not isinstance(self.mode, MoneyValueMode):
            raise InvalidFeedValueError(
                "Нужен типизированный режим денежного значения."
            )
        if self.mode == MoneyValueMode.SOURCE:
            valid = (
                isinstance(self.source, SourceReferenceVO) and self.calculation is None
            )
        elif self.mode == MoneyValueMode.CALCULATED:
            valid = (
                isinstance(self.calculation, PriceCalculationVO) and self.source is None
            )
        else:
            valid = self.source is None and self.calculation is None
        if not valid:
            raise InvalidFeedValueError(
                "Денежное поле требует один согласованный способ получения значения."
            )
