from dataclasses import dataclass
from datetime import date, datetime
from src.modules.currency.application.functional_currency.dto.functional_currency_period_dto import (
    FunctionalCurrencyPeriodDTO,
)
from src.modules.currency.application.policy.dto.currency_policy_dto import (
    CurrencyPolicyDTO,
)
from src.modules.currency.application.provider.dto.provider_status_dto import (
    ProviderStatusDTO,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO


@dataclass(frozen=True, slots=True)
class CurrencySettingsDTO:
    """Organization settings and derived values for the Console summary."""

    configured: bool
    policy: CurrencyPolicyDTO | None
    enabled_currencies: tuple[CurrencyCodeVO, ...]
    periods: tuple[FunctionalCurrencyPeriodDTO, ...]
    functional_currency: CurrencyCodeVO | None
    future_functional_currency: CurrencyCodeVO | None
    business_date: date
    provider_status: ProviderStatusDTO
    default_display_currency: CurrencyCodeVO | None
    next_business_day_at: datetime


__all__ = ["CurrencySettingsDTO"]
