from __future__ import annotations
from dataclasses import dataclass
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ConfigureCurrencyPolicy:
    """Immutable input for configure currency policy."""

    tenant_id: EntityIdVO
    actor_id: EntityIdVO
    policy: CurrencyPolicy
    expected_version: int


__all__ = ["ConfigureCurrencyPolicy"]
