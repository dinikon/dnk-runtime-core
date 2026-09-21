from dataclasses import dataclass
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(frozen=True, slots=True)
class DisplayCurrencyDTO:
    display_currency: CurrencyCodeVO | None


__all__ = ["DisplayCurrencyDTO"]
