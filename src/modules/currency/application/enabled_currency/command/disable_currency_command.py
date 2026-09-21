from dataclasses import dataclass
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class DisableCurrencyCommand:
    """Immutable input for disable currency."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    currency: CurrencyCodeVO


__all__ = ["DisableCurrencyCommand"]
