from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListEnabledCurrenciesQuery:
    """Input for list enabled currencies."""

    tenant_id: EntityIdVO


__all__ = ["ListEnabledCurrenciesQuery"]
