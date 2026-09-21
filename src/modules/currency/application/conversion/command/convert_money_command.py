from dataclasses import dataclass
from src.modules.currency.application.conversion.dto.conversion_request import (
    ConversionRequest,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ConvertMoneyCommand:
    """Immutable input for convert money."""

    tenant_id: EntityIdVO
    request: ConversionRequest


__all__ = ["ConvertMoneyCommand"]
