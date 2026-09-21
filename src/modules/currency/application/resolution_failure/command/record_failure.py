from dataclasses import dataclass
from datetime import date
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class RecordRateResolutionFailure:
    """Immutable input for record rate resolution failure."""

    tenant_id: EntityIdVO
    operation_id: EntityIdVO
    source: CurrencyCodeVO
    target: CurrencyCodeVO | None
    business_date: date | None
    provider: ProviderCode | None
    policy_version: int
    error_code: str


__all__ = ["RecordRateResolutionFailure"]
