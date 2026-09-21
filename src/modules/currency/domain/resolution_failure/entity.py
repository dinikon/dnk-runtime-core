from dataclasses import dataclass
from datetime import date, datetime
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.resolution_failure.value_object.id import (
    ResolutionFailureIdVO,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ResolutionFailure:
    """Deduplicated business failure with its operation and policy provenance."""

    id: ResolutionFailureIdVO
    operation_id: EntityIdVO
    source: CurrencyCodeVO
    target: CurrencyCodeVO | None
    business_date: date | None
    provider: ProviderCode | None
    policy_version: int
    error_code: str
    occurred_at: datetime
    deduplication_key: str


__all__ = ["ResolutionFailure"]
