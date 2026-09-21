from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class FunctionalCurrencyPeriodIdVO(EntityIdVO):
    """Identity of a functional currency record."""


__all__ = ["FunctionalCurrencyPeriodIdVO"]
