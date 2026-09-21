from dataclasses import dataclass
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetCurrencySettingsQuery:
    """Immutable selection criteria for get currency settings."""

    tenant_id: EntityIdVO


__all__ = ["GetCurrencySettingsQuery"]
