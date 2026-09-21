from dataclasses import dataclass
from datetime import date
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetFunctionalCurrencyQuery:
    """Immutable selection criteria for get functional currency."""

    tenant_id: EntityIdVO
    business_date: date


__all__ = ["GetFunctionalCurrencyQuery"]
