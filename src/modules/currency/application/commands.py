from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.currency.domain.models import CurrencyPolicy, CurrencyPair


@dataclass(frozen=True, slots=True)
class ConfigureCurrencyPolicy:
    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    policy: CurrencyPolicy
    expected_version: int


@dataclass(frozen=True, slots=True)
class InitializeCurrency:
    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    policy: CurrencyPolicy
    enabled_currencies: tuple[CurrencyCodeVO, ...]
    functional_currency: CurrencyCodeVO
    valid_from: date
    reason: str


@dataclass(frozen=True, slots=True)
class SetEnabledCurrency:
    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    currency: CurrencyCodeVO
    enabled: bool


@dataclass(frozen=True, slots=True)
class ScheduleFunctionalCurrencyChange:
    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    currency: CurrencyCodeVO
    effective_from: date
    reason: str


@dataclass(frozen=True, slots=True)
class SetManualRate:
    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    pair: CurrencyPair
    rate: Decimal
    effective_date: date
