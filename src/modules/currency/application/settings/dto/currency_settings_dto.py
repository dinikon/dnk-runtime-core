from dataclasses import dataclass
from datetime import date

from src.modules.currency.domain.models import CurrencyPolicy, FunctionalCurrencyPeriod
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(frozen=True, slots=True)
class CurrencySettingsDTO:
    configured: bool
    policy: CurrencyPolicy | None
    enabled_currencies: tuple[CurrencyCodeVO, ...]
    periods: tuple[FunctionalCurrencyPeriod, ...]
    functional_currency: CurrencyCodeVO | None
    future_functional_currency: CurrencyCodeVO | None
    business_date: date
    provider_status: dict
