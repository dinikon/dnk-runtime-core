from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar
from src.modules.feed_builder.domain.feed.validation import decimal


@dataclass(frozen=True, slots=True)
class DecimalLiteralVO:
    """Хранит точную числовую константу без вычисления выражения."""

    kind: ClassVar[str] = "decimal"
    value: Decimal

    def __post_init__(self) -> None:
        """Отклоняет float, бесконечность и чрезмерные литералы без округления."""
        decimal(self.value, label="Decimal literal")
