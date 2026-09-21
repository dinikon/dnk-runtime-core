from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListFunctionalCurrencyPeriodsQuery:
    """Input for list functional currency periods."""

    tenant_id: EntityIdVO


__all__ = ["ListFunctionalCurrencyPeriodsQuery"]
