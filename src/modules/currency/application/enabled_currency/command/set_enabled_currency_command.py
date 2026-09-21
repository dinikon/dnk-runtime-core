from __future__ import annotations
from dataclasses import dataclass
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class SetEnabledCurrency:
    """Immutable input for set enabled currency."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    currency: CurrencyCodeVO
    enabled: bool


__all__ = ["SetEnabledCurrency"]
