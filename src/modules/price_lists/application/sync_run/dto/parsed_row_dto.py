from dataclasses import dataclass
from typing import Any
from src.modules.price_lists.domain.offer.value_object.values import OfferValues


@dataclass(slots=True, frozen=True)
class ParsedRow:
    """Нормализованная строка или ограниченная диагностика ошибки."""

    row_number: int
    normalized: dict[str, Any]
    errors: tuple[str, ...]

    def offer_values(self) -> OfferValues:
        """Возвращает доменные значения проверенной строки."""
        return OfferValues(
            **{
                name: self.normalized.get(name)
                for name in OfferValues.__dataclass_fields__
            }
        )


__all__ = ["ParsedRow"]
