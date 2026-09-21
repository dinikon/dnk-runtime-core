from dataclasses import dataclass
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ValidateDisplayCurrencyQuery:
    """Immutable selection criteria for validate display currency."""

    tenant_id: EntityIdVO
    currency: CurrencyCodeVO


__all__ = ["ValidateDisplayCurrencyQuery"]
